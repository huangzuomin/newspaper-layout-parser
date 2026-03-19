"""
Headline rewrite generator.
"""

import logging
from typing import Any, Dict, List

from .llm_enhanced_generator import LLMEnhancedGenerator
from .rewrite_strategies import RewriteStrategyEngine
from ..models.headline_rewrite import (
    HeadlineContext,
    HeadlineDiagnosis,
    HeadlineRewriteResult,
    OptimizationSuggestion,
    RewriteCandidate,
    RewriteStyle,
    RiskLevel,
    SuggestionType,
)
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger("intelligent_editor")


class HeadlineRewriteGenerator:
    """Generate rewrite suggestions for weak headlines."""

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = ConfigLoader.load_config("rewrite_templates.yaml")

        self.config = config
        self.strategy_engine = RewriteStrategyEngine(config)
        self.llm_generator = LLMEnhancedGenerator(config.get("llm_config", {}))
        logger.info("HeadlineRewriteGenerator initialized")

    def generate_rewrite(self, context: HeadlineContext) -> HeadlineRewriteResult:
        article_id = context.article_id
        headline_text = context.headline_text
        headline_block_id = context.headline_block_id or context.article_id

        diagnosis = self._diagnose_headline(context)
        need_optimization = self._needs_optimization(context, diagnosis)

        if not need_optimization:
            return HeadlineRewriteResult(
                article_id=article_id,
                headline_block_id=headline_block_id,
                original_headline=headline_text,
                original_length=len(headline_text),
                need_optimization=False,
                diagnosis=diagnosis,
                suggestions=[],
                rewrite_candidates=[],
                metadata={"reason": "headline quality is acceptable"},
            )

        suggestions = self._generate_suggestions(context)
        candidates = self._rank_and_limit_candidates(self._generate_candidates(context))

        return HeadlineRewriteResult(
            article_id=article_id,
            headline_block_id=headline_block_id,
            original_headline=headline_text,
            original_length=len(headline_text),
            need_optimization=True,
            diagnosis=diagnosis,
            suggestions=suggestions,
            rewrite_candidates=candidates,
            metadata={
                "candidate_count": len(candidates),
                "generation_method": "hybrid" if self.llm_generator.is_available() else "rule",
            },
        )

    def _diagnose_headline(self, context: HeadlineContext) -> HeadlineDiagnosis:
        headline = context.headline_text
        problems: List[str] = []
        if "too_long" in context.issue_tags:
            problems.append(f"headline too long ({len(headline)} chars)")
        if "too_generic" in context.issue_tags:
            problems.append("headline too generic")
        if "meeting_style_heavy" in context.issue_tags:
            problems.append("meeting-style wording dominates")
        if "repetitive_with_kicker" in context.issue_tags:
            problems.append("repeats kicker information")
        if "weak_focus" in context.issue_tags:
            problems.append("focus is weak")

        analysis_parts: List[str] = []
        if len(headline) > 20:
            analysis_parts.append("length exceeds configured threshold")
        for generic_word in ("\u8fdb\u4e00\u6b65", "\u5207\u5b9e", "\u624e\u5b9e", "\u5168\u9762"):
            if generic_word in headline:
                analysis_parts.append(f"contains generic term {generic_word}")

        return HeadlineDiagnosis(
            core_problem="; ".join(problems) if problems else "headline is acceptable",
            confidence=0.9 if context.issue_tags else 0.6,
            issue_tags=list(context.issue_tags),
            analysis="; ".join(analysis_parts) if analysis_parts else "no major structural issue found",
        )

    def _needs_optimization(self, context: HeadlineContext, diagnosis: HeadlineDiagnosis) -> bool:
        return bool(context.issue_tags) or len(context.headline_text) > 20 or diagnosis.confidence >= 0.8

    def _generate_suggestions(self, context: HeadlineContext) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []

        if "too_long" in context.issue_tags:
            suggestions.append(
                OptimizationSuggestion(
                    type=SuggestionType.DIRECTIONAL,
                    message="Compress filler wording and keep the action or result.",
                    reasoning="Long headlines weaken focus.",
                )
            )

        if "meeting_style_heavy" in context.issue_tags:
            suggestions.append(
                OptimizationSuggestion(
                    type=SuggestionType.MICRO_EDIT,
                    message="Reduce meeting-process phrasing and foreground the actual outcome.",
                    reasoning="Readers care more about the result than the meeting itself.",
                )
            )

        if "too_generic" in context.issue_tags:
            suggestions.append(
                OptimizationSuggestion(
                    type=SuggestionType.DIRECTIONAL,
                    message="Add a more concrete actor, action, result, or impact.",
                    reasoning="Generic headlines have low information density.",
                )
            )

        if "repetitive_with_kicker" in context.issue_tags and context.kicker_text:
            suggestions.append(
                OptimizationSuggestion(
                    type=SuggestionType.MICRO_EDIT,
                    message=f"Remove wording that repeats the kicker: {context.kicker_text}",
                    reasoning="The kicker already carries that information.",
                )
            )

        if "weak_focus" in context.issue_tags:
            suggestions.append(
                OptimizationSuggestion(
                    type=SuggestionType.STRUCTURAL,
                    message="Keep one clear focus and foreground the most newsworthy element.",
                    reasoning="A single strong focus reads better than a broad summary.",
                )
            )

        return suggestions

    def _generate_candidates(self, context: HeadlineContext) -> List[RewriteCandidate]:
        candidates = list(self.strategy_engine.generate_rewrites(context))
        if self.llm_generator.is_available() and len(context.issue_tags) > 2:
            candidates.extend(self._generate_llm_candidates(context))
        return candidates

    def _generate_llm_candidates(self, context: HeadlineContext) -> List[RewriteCandidate]:
        candidates: List[RewriteCandidate] = []
        for style in (RewriteStyle.CONSERVATIVE, RewriteStyle.FOCUSED):
            try:
                candidates.extend(
                    self.llm_generator.generate_with_llm(context, style, num_variations=1)
                )
            except Exception as exc:
                logger.error("LLM generation failed for %s: %s", style.value, exc)
        return candidates

    def _rank_and_limit_candidates(
        self, candidates: List[RewriteCandidate]
    ) -> List[RewriteCandidate]:
        risk_priority = {
            RiskLevel.SAFE: 0,
            RiskLevel.USABLE_WITH_REVIEW: 1,
            RiskLevel.NOT_RECOMMENDED: 2,
        }
        candidates.sort(key=lambda item: (risk_priority.get(item.risk_level, 1), -item.confidence))
        return candidates[:3]
