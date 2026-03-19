"""
Headline quality analyzer.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from ..models.editorial_quality import HeadlineIssueType, HeadlineSuggestion, ImpactLevel
from ..models.headline_rewrite import HeadlineContext, PolicyConstraints

logger = logging.getLogger("intelligent_editor")


class HeadlineAnalyzer:
    MEETING_STYLE_PATTERNS = [
        r"\u53ec\u5f00",
        r"\u5b66\u4e60\u8d2f\u5f7b",
        r"\u7814\u7a76\u90e8\u7f72",
        r"\u542c\u53d6",
        r"\u5f3a\u8c03",
        r"\u6307\u51fa",
        r"\u5e38\u59d4\u4f1a\u4f1a\u8bae",
        r"\u515a\u7ec4\u4f1a\u8bae",
        r"\u5e38\u52a1\u4f1a\u8bae",
        r"\u4e13\u9898\u4f1a\u8bae",
    ]
    GENERIC_PATTERNS = [
        r"\u8fdb\u4e00\u6b65",
        r"\u5207\u5b9e",
        r"\u624e\u5b9e",
        r"\u5168\u9762",
        r"\u6df1\u5165",
        r"\u5927\u529b",
        r"\u79ef\u6781",
        r"\u52aa\u529b",
        r"\u52a0\u5f3a.*\u5efa\u8bbe",
        r"\u63a8\u52a8.*\u53d1\u5c55",
    ]
    WEAK_FOCUS_PATTERNS = [
        r"^.{0,5}\u5de5\u4f5c$",
        r"^.{0,10}\u6d3b\u52a8$",
        r"^.{0,10}\u5de5\u7a0b$",
        r"\u6709\u5173.*\u5de5\u4f5c",
        r"\u76f8\u5173.*\u4e8b\u9879",
        r"\u82e5\u5e72.*\u95ee\u9898",
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_length = config.get("max_headline_length", 20)
        self.ideal_length = config.get("ideal_headline_length", 12)
        self.min_length = config.get("min_headline_length", 6)
        self.rewrite_generator = None

        try:
            from .headline_rewrite_generator import HeadlineRewriteGenerator

            rewrite_config = config.get("headline_rewrite", {})
            if rewrite_config.get("enabled", False):
                self.rewrite_generator = HeadlineRewriteGenerator(rewrite_config)
        except ImportError as exc:
            logger.warning("Could not import HeadlineRewriteGenerator: %s", exc)

    def analyze_headlines(self, structured_data: Dict[str, Any]) -> List[HeadlineSuggestion]:
        suggestions: List[HeadlineSuggestion] = []
        blocks_by_id = {block.get("id"): block for block in structured_data.get("blocks", [])}

        for article in structured_data.get("articles", []):
            article_id = article.get("id", "")
            headline_block = blocks_by_id.get(article.get("headline_block_id"))
            if not headline_block:
                continue

            headline_text = headline_block.get("text", "").strip()
            if not headline_text:
                continue

            suggestion = self._check_headline_quality(
                article=article,
                article_id=article_id,
                headline_block=headline_block,
                headline_text=headline_text,
                blocks_by_id=blocks_by_id,
            )
            if suggestion:
                suggestions.append(suggestion)

        logger.info("Generated %s headline suggestions", len(suggestions))
        return suggestions

    def _check_headline_quality(
        self,
        article: Dict[str, Any],
        article_id: str,
        headline_block: Dict[str, Any],
        headline_text: str,
        blocks_by_id: Dict[str, Dict[str, Any]],
    ) -> Optional[HeadlineSuggestion]:
        if len(headline_text) > self.max_length:
            return self._create_too_long_suggestion(article, article_id, headline_block, blocks_by_id)
        if self._is_meeting_style(headline_text):
            return self._create_meeting_style_suggestion(article, article_id, headline_block, blocks_by_id)
        if self._is_too_generic(headline_text):
            return self._create_generic_suggestion(article, article_id, headline_block, blocks_by_id)
        if self._is_weak_focus(headline_text):
            return self._create_weak_focus_suggestion(article_id, headline_text)

        kicker_text = self._extract_kicker_text(article, blocks_by_id)
        if kicker_text and kicker_text in headline_text:
            return HeadlineSuggestion(
                id=f"headline_kicker_repetition_{article_id}",
                article_id=article_id,
                headline_text=headline_text,
                issue_type=HeadlineIssueType.REPETITIVE_WITH_KICKER,
                issue_description="Headline repeats kicker information",
                reason="The headline reuses information already carried by the kicker/subheadline.",
                current_approach=f"Current headline: {headline_text}",
                lightweight_suggestion="Trim repeated wording from the headline and keep only incremental information.",
                alternative_headlines=self._generate_rewrite_candidates(
                    article,
                    article_id,
                    headline_block,
                    blocks_by_id,
                    ["repetitive_with_kicker"],
                ),
                impact_level=ImpactLevel.MEDIUM,
                expected_improvement="Reduces redundancy and raises headline density.",
                confidence=0.9,
                metadata={"kicker_text": kicker_text},
            )

        return None

    def _create_too_long_suggestion(
        self,
        article: Dict[str, Any],
        article_id: str,
        headline_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
    ) -> HeadlineSuggestion:
        headline_text = headline_block.get("text", "")
        return HeadlineSuggestion(
            id=f"headline_too_long_{article_id}",
            article_id=article_id,
            headline_text=headline_text,
            issue_type=HeadlineIssueType.TOO_LONG,
            issue_description=f"Headline is too long ({len(headline_text)} chars)",
            reason="The headline exceeds the configured length budget.",
            current_approach=f"Current headline length: {len(headline_text)}",
            lightweight_suggestion=f"Compress to about {self.ideal_length}-{self.max_length} characters.",
            alternative_headlines=self._generate_rewrite_candidates(
                article, article_id, headline_block, blocks_by_id, ["too_long"]
            ),
            impact_level=ImpactLevel.MEDIUM,
            expected_improvement="A tighter headline is easier to scan.",
            confidence=0.8,
            metadata={"current_length": len(headline_text)},
        )

    def _create_meeting_style_suggestion(
        self,
        article: Dict[str, Any],
        article_id: str,
        headline_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
    ) -> HeadlineSuggestion:
        headline_text = headline_block.get("text", "")
        return HeadlineSuggestion(
            id=f"headline_meeting_style_{article_id}",
            article_id=article_id,
            headline_text=headline_text,
            issue_type=HeadlineIssueType.MEETING_STYLE_HEAVY,
            issue_description="Headline is too meeting-style",
            reason="Process language dominates over result or impact.",
            current_approach=f"Current headline: {headline_text}",
            lightweight_suggestion="Reduce process verbs and foreground the actual outcome or action.",
            alternative_headlines=self._generate_rewrite_candidates(
                article, article_id, headline_block, blocks_by_id, ["meeting_style_heavy"]
            ),
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Makes the headline more news-oriented.",
            confidence=0.9,
            metadata={},
        )

    def _create_generic_suggestion(
        self,
        article: Dict[str, Any],
        article_id: str,
        headline_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
    ) -> HeadlineSuggestion:
        headline_text = headline_block.get("text", "")
        generic_words = self._find_generic_words(headline_text)
        return HeadlineSuggestion(
            id=f"headline_generic_{article_id}",
            article_id=article_id,
            headline_text=headline_text,
            issue_type=HeadlineIssueType.TOO_GENERIC,
            issue_description="Headline is too generic",
            reason=f"Generic terms found: {', '.join(generic_words) or 'none'}",
            current_approach=f"Current headline: {headline_text}",
            lightweight_suggestion="Add a more concrete actor, action, result, or impact.",
            alternative_headlines=self._generate_rewrite_candidates(
                article, article_id, headline_block, blocks_by_id, ["too_generic"]
            ),
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Raises information density.",
            confidence=0.85,
            metadata={"generic_words": generic_words},
        )

    def _create_weak_focus_suggestion(self, article_id: str, headline_text: str) -> HeadlineSuggestion:
        return HeadlineSuggestion(
            id=f"headline_weak_focus_{article_id}",
            article_id=article_id,
            headline_text=headline_text,
            issue_type=HeadlineIssueType.WEAK_FOCUS,
            issue_description="Headline focus is weak",
            reason="The most newsworthy element is not clearly foregrounded.",
            current_approach=f"Current headline: {headline_text}",
            lightweight_suggestion="Keep one clear focus and foreground the strongest action or result.",
            alternative_headlines=["[focus action]", "[focus result]", "[focus impact]"],
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Improves clarity and readability.",
            confidence=0.8,
            metadata={},
        )

    def _generate_rewrite_candidates(
        self,
        article: Dict[str, Any],
        article_id: str,
        headline_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
        issue_tags: List[str],
    ) -> List[str]:
        if not self.rewrite_generator:
            return []

        context = HeadlineContext(
            article_id=article_id,
            headline_block_id=headline_block.get("id", ""),
            headline_text=headline_block.get("text", ""),
            kicker_text=self._extract_kicker_text(article, blocks_by_id),
            subheadline_text=self._extract_subheadline_text(article, blocks_by_id),
            lead_text=self._extract_lead_text(article, blocks_by_id),
            body_summary=self._extract_body_summary(article, blocks_by_id),
            issue_tags=issue_tags,
            policy_constraints=PolicyConstraints(),
        )

        try:
            result = self.rewrite_generator.generate_rewrite(context)
        except Exception as exc:
            logger.error("Error generating rewrite candidates: %s", exc)
            return []

        return [
            f"[{candidate.style.value}] {candidate.headline}\n  changes: {candidate.changes}\n  risk: {candidate.risk_note}"
            for candidate in result.rewrite_candidates
        ]

    def _extract_kicker_text(
        self, article: Dict[str, Any], blocks_by_id: Dict[str, Dict[str, Any]]
    ) -> str:
        subheadline = blocks_by_id.get(article.get("subheadline_block_id"))
        return (subheadline or {}).get("text", "").strip()

    def _extract_subheadline_text(
        self, article: Dict[str, Any], blocks_by_id: Dict[str, Dict[str, Any]]
    ) -> str:
        subheadline = blocks_by_id.get(article.get("subheadline_block_id"))
        return (subheadline or {}).get("text", "").strip()

    def _extract_lead_text(
        self, article: Dict[str, Any], blocks_by_id: Dict[str, Dict[str, Any]]
    ) -> str:
        parts: List[str] = []
        for block_id in article.get("body_block_ids", [])[:3]:
            text = (blocks_by_id.get(block_id) or {}).get("text", "").strip()
            if text:
                parts.append(text)
        return " ".join(parts)[:200]

    def _extract_body_summary(
        self, article: Dict[str, Any], blocks_by_id: Dict[str, Dict[str, Any]]
    ) -> str:
        parts: List[str] = []
        for block_id in article.get("body_block_ids", [])[:5]:
            text = (blocks_by_id.get(block_id) or {}).get("text", "").strip()
            if text:
                parts.append(text)
        return " ".join(parts)[:300]

    def _is_meeting_style(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in self.MEETING_STYLE_PATTERNS)

    def _is_too_generic(self, text: str) -> bool:
        return sum(1 for pattern in self.GENERIC_PATTERNS if re.search(pattern, text)) >= 2

    def _is_weak_focus(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in self.WEAK_FOCUS_PATTERNS)

    def _find_generic_words(self, headline: str) -> List[str]:
        found: List[str] = []
        for pattern in self.GENERIC_PATTERNS:
            match = re.search(pattern, headline)
            if match:
                found.append(match.group())
        return found
