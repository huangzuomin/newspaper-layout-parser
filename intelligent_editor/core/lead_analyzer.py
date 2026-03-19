"""
Lead quality analyzer.
"""

import logging
import re
from typing import Any, Dict, List

from ..models.editorial_quality import ImpactLevel, LeadIssueType, LeadSuggestion

logger = logging.getLogger("intelligent_editor")


class LeadAnalyzer:
    SLOW_START_PATTERNS = [
        r"^\u4e3a\u4e86.*?[\uff0c,]",
        r"^\u8fd1\u65e5$|^\u65e5\u524d$|^\u8fd1\u65e5\u6765",
        r"^\u968f\u7740.*?[\uff0c,]",
        r"^\u5728.*?\u4e2d",
        r"^\u5173\u4e8e.*?[\uff0c,]",
    ]
    ABSTRACT_PATTERNS = [
        r"\u8fdb\u4e00\u6b65.*?(?:\u52a0\u5f3a|\u6df1\u5316|\u63a8\u8fdb|\u63d0\u5347)",
        r"\u5207\u5b9e.*?(?:\u505a\u597d|\u6293\u597d|\u843d\u5b9e)",
        r"\u5168\u9762.*?(?:\u52a0\u5f3a|\u63a8\u8fdb|\u63d0\u5347)",
        r"\u6df1\u5165.*?(?:\u8d2f\u5f7b|\u843d\u5b9e|\u63a8\u8fdb)",
        r"\u624e\u5b9e.*?(?:\u505a\u597d|\u63a8\u8fdb)",
        r"\u5927\u529b.*?(?:\u53d1\u5c55|\u63a8\u8fdb|\u52a0\u5f3a)",
    ]
    NEWS_VALUE_KEYWORDS = [
        "\u7a81\u7834",
        "\u9996\u6b21",
        "\u521b\u65b0",
        "\u91cd\u5927",
        "\u91cd\u8981",
        "\u5173\u952e",
        "\u65b0\u589e",
        "\u589e\u957f",
        "\u4e0b\u964d",
        "\u63d0\u5347",
        "\u6539\u5584",
        "\u5b9e\u73b0",
        "\u5b8c\u6210",
        "\u8fbe\u6210",
        "\u53d6\u5f97",
        "\u83b7\u5f97",
        "\u53d1\u5e03",
        "\u63a8\u51fa",
        "\u542f\u52a8",
        "\u5f00\u5c55",
        "\u5b9e\u65bd",
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_lead_length = config.get("max_lead_length", 150)
        self.min_lead_length = config.get("min_lead_length", 30)

    def analyze_leads(
        self,
        structured_data: Dict[str, Any],
        headline_suggestions: Dict[str, Any] = None,
    ) -> List[LeadSuggestion]:
        suggestions: List[LeadSuggestion] = []
        blocks_by_id = {block.get("id"): block for block in structured_data.get("blocks", [])}

        for article in structured_data.get("articles", []):
            article_id = article.get("id", "")
            lead_text = self._extract_lead(article, blocks_by_id)
            if not lead_text:
                continue

            headline_text = (
                (blocks_by_id.get(article.get("headline_block_id")) or {}).get("text", "").strip()
            )
            suggestion = self._check_lead_quality(lead_text, article_id, headline_text, article)
            if suggestion:
                suggestions.append(suggestion)

        logger.info("Generated %s lead suggestions", len(suggestions))
        return suggestions

    def _extract_lead(self, article: Dict[str, Any], blocks_by_id: Dict[str, Dict[str, Any]]) -> str:
        parts: List[str] = []
        for block_id in article.get("body_block_ids", [])[:3]:
            text = (blocks_by_id.get(block_id) or {}).get("text", "").strip()
            if text:
                parts.append(text)
        return " ".join(parts)

    def _check_lead_quality(
        self,
        lead_text: str,
        article_id: str,
        headline_text: str,
        article: Dict[str, Any],
    ) -> LeadSuggestion:
        if headline_text and self._is_repeated_with_headline(lead_text, headline_text):
            return self._create_repetition_suggestion(lead_text, headline_text, article_id)
        if self._is_slow_start(lead_text):
            return self._create_slow_start_suggestion(lead_text, article_id)
        if self._is_too_abstract(lead_text):
            return self._create_abstract_suggestion(lead_text, article_id)
        if not self._has_news_value_frontloaded(lead_text):
            return self._create_news_value_suggestion(lead_text, article_id)
        return None

    def _is_repeated_with_headline(self, lead: str, headline: str) -> bool:
        headline_tokens = self._tokenize_text(headline)
        lead_tokens = self._tokenize_text(lead[:60])
        if not headline_tokens:
            return False
        overlap = len(headline_tokens & lead_tokens) / len(headline_tokens)
        return overlap >= 0.5 or headline[:8] in lead[:40]

    def _tokenize_text(self, text: str) -> set:
        normalized = re.sub(r"[\u3001\u3002\uff0c\uff1a\uff1b\uff01\uff1f\s]", "", text)
        tokens = set()

        for idx in range(len(normalized)):
            token = normalized[idx : idx + 2]
            if len(token) == 2:
                tokens.add(token)

        for match in re.findall(r"[A-Za-z0-9]+", text):
            tokens.add(match.lower())

        return tokens

    def _is_slow_start(self, lead: str) -> bool:
        return any(re.match(pattern, lead) for pattern in self.SLOW_START_PATTERNS)

    def _is_too_abstract(self, lead: str) -> bool:
        return sum(1 for pattern in self.ABSTRACT_PATTERNS if re.search(pattern, lead)) >= 2

    def _has_news_value_frontloaded(self, lead: str) -> bool:
        lead_start = lead[:50]
        return any(keyword in lead_start for keyword in self.NEWS_VALUE_KEYWORDS)

    def _create_repetition_suggestion(
        self, lead_text: str, headline_text: str, article_id: str
    ) -> LeadSuggestion:
        overlap = self._find_overlap(lead_text, headline_text)
        return LeadSuggestion(
            id=f"lead_repetition_{article_id}",
            article_id=article_id,
            lead_text=lead_text,
            issue_type=LeadIssueType.REPEATED_WITH_HEADLINE,
            issue_description="Lead repeats the headline",
            reason=f"Repeated tokens: {overlap or 'high overlap'}",
            current_approach="The opening of the lead duplicates the headline.",
            lightweight_suggestion="Use the lead for incremental facts such as time, place, result, or impact.",
            revised_lead_example=self._revise_repetition_lead(lead_text, overlap),
            impact_level=ImpactLevel.MEDIUM,
            expected_improvement="Improves density and reduces repetition.",
            confidence=0.85,
            metadata={"overlap": overlap},
        )

    def _create_slow_start_suggestion(self, lead_text: str, article_id: str) -> LeadSuggestion:
        return LeadSuggestion(
            id=f"lead_slow_start_{article_id}",
            article_id=article_id,
            lead_text=lead_text,
            issue_type=LeadIssueType.SLOW_START,
            issue_description="Lead starts too slowly",
            reason="Background language delays the core fact.",
            current_approach="The lead spends too much space on setup.",
            lightweight_suggestion="Move the key fact or result to the first sentence.",
            revised_lead_example=self._revise_slow_start_lead(lead_text),
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Readers can identify the news point faster.",
            confidence=0.85,
            metadata={},
        )

    def _create_abstract_suggestion(self, lead_text: str, article_id: str) -> LeadSuggestion:
        abstract_terms = []
        for pattern in self.ABSTRACT_PATTERNS:
            match = re.search(pattern, lead_text)
            if match:
                abstract_terms.append(match.group())

        return LeadSuggestion(
            id=f"lead_abstract_{article_id}",
            article_id=article_id,
            lead_text=lead_text,
            issue_type=LeadIssueType.ABSTRACT_OPENING,
            issue_description="Lead is too abstract",
            reason=f"Abstract patterns found: {', '.join(abstract_terms[:3]) or 'generic wording'}",
            current_approach="The lead uses abstract or generic wording.",
            lightweight_suggestion="Replace abstractions with concrete facts, actors, actions, or outcomes.",
            revised_lead_example=self._revise_abstract_lead(lead_text, abstract_terms),
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Makes the lead more concrete and credible.",
            confidence=0.8,
            metadata={"abstract_terms": abstract_terms},
        )

    def _create_news_value_suggestion(self, lead_text: str, article_id: str) -> LeadSuggestion:
        return LeadSuggestion(
            id=f"lead_news_value_{article_id}",
            article_id=article_id,
            lead_text=lead_text,
            issue_type=LeadIssueType.INSUFFICIENT_NEWS_VALUE_FRONTLOADING,
            issue_description="News value is not front-loaded",
            reason="The lead does not foreground the result, change, or impact early enough.",
            current_approach="High-value information appears too late.",
            lightweight_suggestion="Front-load the most newsworthy outcome or change.",
            revised_lead_example=self._revise_news_value_lead(lead_text),
            impact_level=ImpactLevel.HIGH,
            expected_improvement="Improves scanability and reader attention.",
            confidence=0.75,
            metadata={},
        )

    def _find_overlap(self, lead: str, headline: str) -> str:
        overlap = list(self._tokenize_text(lead[:40]) & self._tokenize_text(headline))
        return " ".join(overlap[:5])

    def _revise_repetition_lead(self, lead: str, overlap: str) -> str:
        sentences = [segment.strip() for segment in re.split(r"[\u3002\uff01\uff1f]", lead) if segment.strip()]
        kept = [sentence for sentence in sentences if overlap and overlap not in sentence]
        return "\u3002".join(kept) if kept else lead

    def _revise_slow_start_lead(self, lead: str) -> str:
        sentences = [segment.strip() for segment in re.split(r"[\u3002\uff01\uff1f]", lead) if segment.strip()]
        return "\u3002".join(sentences[1:]) if len(sentences) > 1 else lead

    def _revise_abstract_lead(self, lead: str, abstract_terms: List[str]) -> str:
        revised = lead
        for term in abstract_terms[:3]:
            revised = revised.replace(term, "")
        return revised.strip() or lead

    def _revise_news_value_lead(self, lead: str) -> str:
        return "[front-load the most newsworthy result or change]"
