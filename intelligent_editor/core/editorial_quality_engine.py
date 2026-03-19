"""
Editorial quality engine.
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List

from .headline_analyzer import HeadlineAnalyzer
from .lead_analyzer import LeadAnalyzer
from ..models.editorial_quality import (
    EditorialQualityAssessment,
    HeadlineSuggestion,
    HomogeneitySuggestion,
    ImpactLevel,
    ImprovementSuggestion,
    ImprovementTarget,
    LeadSuggestion,
    PackagingIssueType,
    PackagingSuggestion,
    QualityImprovementReport,
)

logger = logging.getLogger("intelligent_editor")


class EditorialQualityEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        headline_config = {
            **config.get("headline_analysis", {}),
            "headline_rewrite": config.get("headline_rewrite", {}),
        }
        lead_config = config.get("lead_analysis", {})
        self.headline_analyzer = HeadlineAnalyzer(headline_config)
        self.lead_analyzer = LeadAnalyzer(lead_config)

    def generate_quality_assessment(
        self,
        structured_data: Dict[str, Any],
        metrics: Dict[str, Any],
        risks: List[Any] = None,
    ) -> QualityImprovementReport:
        headline_suggestions = self.headline_analyzer.analyze_headlines(structured_data)
        lead_suggestions = self.lead_analyzer.analyze_leads(structured_data, headline_suggestions)
        packaging_suggestions = self._analyze_packaging(structured_data, metrics)
        homogeneity_suggestions = self._analyze_homogeneity(structured_data)

        assessment = self._create_assessment(
            structured_data,
            headline_suggestions,
            lead_suggestions,
            packaging_suggestions,
            homogeneity_suggestions,
            metrics,
        )

        top_improvements = self._extract_top_improvements(
            headline_suggestions,
            lead_suggestions,
            packaging_suggestions,
            homogeneity_suggestions,
        )

        all_suggestions = (
            headline_suggestions
            + lead_suggestions
            + packaging_suggestions
            + homogeneity_suggestions
        )

        high_count = sum(1 for item in all_suggestions if item.impact_level == ImpactLevel.HIGH)
        medium_count = sum(1 for item in all_suggestions if item.impact_level == ImpactLevel.MEDIUM)
        low_count = sum(1 for item in all_suggestions if item.impact_level == ImpactLevel.LOW)

        report = QualityImprovementReport(
            assessment=assessment,
            top_improvement_points=top_improvements,
            headline_suggestions=headline_suggestions,
            lead_suggestions=lead_suggestions,
            packaging_suggestions=packaging_suggestions,
            homogeneity_suggestions=homogeneity_suggestions,
            total_suggestions=len(all_suggestions),
            high_impact_count=high_count,
            medium_impact_count=medium_count,
            low_impact_count=low_count,
        )

        logger.info("Generated quality report: %s suggestions", len(all_suggestions))
        return report

    def _analyze_packaging(
        self, structured_data: Dict[str, Any], metrics: Dict[str, Any]
    ) -> List[PackagingSuggestion]:
        suggestions: List[PackagingSuggestion] = []
        articles = structured_data.get("articles", [])
        blocks = structured_data.get("blocks", [])
        blocks_by_id = {block.get("id"): block for block in blocks}

        total_images = sum(len(article.get("image_block_ids", [])) for article in articles)
        if len(articles) >= 3 and total_images == 0:
            suggestions.append(
                PackagingSuggestion(
                    id="packaging_no_images",
                    article_id="page",
                    issue_type=PackagingIssueType.PHOTO_WEAK_TEXT,
                    issue_description="Page has no image support",
                    reason="A multi-story page without any image support can feel visually heavy.",
                    current_state="No image blocks were attached to any article.",
                    lightweight_suggestion="Consider adding at least one supporting image or infographic.",
                    impact_level=ImpactLevel.MEDIUM,
                    expected_improvement="Improves visual rhythm and reduces text density.",
                    confidence=0.7,
                )
            )

        headline_sizes = []
        for article in articles:
            headline = blocks_by_id.get(article.get("headline_block_id"))
            if headline and headline.get("font_size"):
                headline_sizes.append(float(headline["font_size"]))

        if len(headline_sizes) >= 2 and max(headline_sizes) - min(headline_sizes) < 2:
            suggestions.append(
                PackagingSuggestion(
                    id="packaging_low_hierarchy",
                    article_id="page",
                    issue_type=PackagingIssueType.LOW_VISUAL_HIERARCHY,
                    issue_description="Visual hierarchy among headlines is weak",
                    reason="Headline sizes are too similar across articles, which weakens page hierarchy.",
                    current_state=f"Headline size spread is only {max(headline_sizes) - min(headline_sizes):.1f}pt.",
                    lightweight_suggestion="Increase size contrast between primary and secondary stories.",
                    impact_level=ImpactLevel.MEDIUM,
                    expected_improvement="Makes the lead story clearer and the page easier to scan.",
                    confidence=0.8,
                )
            )

        return suggestions

    def _analyze_homogeneity(
        self, structured_data: Dict[str, Any]
    ) -> List[HomogeneitySuggestion]:
        suggestions: List[HomogeneitySuggestion] = []
        blocks_by_id = {block.get("id"): block for block in structured_data.get("blocks", [])}

        headline_pairs = []
        for article in structured_data.get("articles", []):
            article_id = article.get("id")
            headline = (blocks_by_id.get(article.get("headline_block_id")) or {}).get("text", "").strip()
            if headline:
                headline_pairs.append((article_id, headline))

        if len(headline_pairs) < 3:
            return suggestions

        prefixes = Counter(self._headline_prefix(text) for _, text in headline_pairs if self._headline_prefix(text))
        repeated_prefixes = {prefix for prefix, count in prefixes.items() if count >= 2}
        if repeated_prefixes:
            article_ids = [
                article_id
                for article_id, headline in headline_pairs
                if self._headline_prefix(headline) in repeated_prefixes
            ]
            suggestions.append(
                HomogeneitySuggestion(
                    id="homogeneity_repeated_prefix",
                    article_ids=article_ids,
                    issue_type="expression_homogeneity",
                    issue_description="Multiple headlines share the same opening pattern",
                    reason="Several headlines begin with the same phrase or structural pattern.",
                    similarity_analysis=", ".join(sorted(repeated_prefixes)),
                    lightweight_suggestion="Vary headline openings so adjacent stories do not sound interchangeable.",
                    impact_level=ImpactLevel.MEDIUM,
                    expected_improvement="Improves page diversity and editorial distinctiveness.",
                    confidence=0.7,
                )
            )

        return suggestions

    def _headline_prefix(self, headline: str) -> str:
        normalized = re.sub(r"\s+", " ", headline).strip()
        return normalized[:6]

    def _create_assessment(
        self,
        structured_data: Dict[str, Any],
        headline_suggestions: List[HeadlineSuggestion],
        lead_suggestions: List[LeadSuggestion],
        packaging_suggestions: List[PackagingSuggestion],
        homogeneity_suggestions: List[HomogeneitySuggestion],
        metrics: Dict[str, Any],
    ) -> EditorialQualityAssessment:
        headline_score = self._calculate_score(headline_suggestions)
        lead_score = self._calculate_score(lead_suggestions)
        packaging_score = self._calculate_score(packaging_suggestions)
        diversity_score = self._calculate_score(homogeneity_suggestions)

        overall_score = (
            headline_score * 0.4
            + lead_score * 0.3
            + packaging_score * 0.2
            + diversity_score * 0.1
        )
        grade = self._score_to_grade(overall_score)

        assessment_text = self._generate_overall_assessment(
            overall_score,
            headline_suggestions,
            lead_suggestions,
            packaging_suggestions,
            homogeneity_suggestions,
        )

        strengths = self._identify_strengths(
            headline_score, lead_score, packaging_score, diversity_score
        )
        improvement_areas = self._identify_improvement_areas(
            headline_score,
            lead_score,
            packaging_score,
            diversity_score,
            headline_suggestions,
            lead_suggestions,
            packaging_suggestions,
            homogeneity_suggestions,
        )

        return EditorialQualityAssessment(
            overall_score=overall_score,
            overall_grade=grade,
            overall_editorial_assessment=assessment_text,
            strengths=strengths,
            improvement_areas=improvement_areas,
            headline_quality_score=headline_score,
            lead_quality_score=lead_score,
            packaging_quality_score=packaging_score,
            diversity_score=diversity_score,
        )

    def _calculate_score(self, suggestions: List[Any]) -> float:
        penalty = 0
        for suggestion in suggestions:
            if suggestion.impact_level == ImpactLevel.HIGH:
                penalty += 12
            elif suggestion.impact_level == ImpactLevel.MEDIUM:
                penalty += 6
            else:
                penalty += 3
        return max(0.0, 100.0 - penalty)

    def _score_to_grade(self, score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    def _generate_overall_assessment(
        self,
        score: float,
        headline_suggestions: List[HeadlineSuggestion],
        lead_suggestions: List[LeadSuggestion],
        packaging_suggestions: List[PackagingSuggestion],
        homogeneity_suggestions: List[HomogeneitySuggestion],
    ) -> str:
        if score >= 90:
            return "Editorial quality is strong and requires only minor tuning."
        if packaging_suggestions or homogeneity_suggestions:
            return "Core stories are workable, but packaging and page diversity still need attention."
        if headline_suggestions or lead_suggestions:
            return "The page is usable, but headline and lead quality still leave room for improvement."
        return "Editorial quality is mixed and needs focused revision."

    def _identify_strengths(
        self,
        headline_score: float,
        lead_score: float,
        packaging_score: float,
        diversity_score: float,
    ) -> List[str]:
        strengths: List[str] = []
        if headline_score >= 85:
            strengths.append("Headline quality is relatively stable")
        if lead_score >= 85:
            strengths.append("Lead structure is generally solid")
        if packaging_score >= 85:
            strengths.append("Page packaging is reasonably balanced")
        if diversity_score >= 85:
            strengths.append("Story presentation remains diverse")
        if not strengths:
            strengths.append("No standout strength identified yet")
        return strengths

    def _identify_improvement_areas(
        self,
        headline_score: float,
        lead_score: float,
        packaging_score: float,
        diversity_score: float,
        headline_suggestions: List[HeadlineSuggestion],
        lead_suggestions: List[LeadSuggestion],
        packaging_suggestions: List[PackagingSuggestion],
        homogeneity_suggestions: List[HomogeneitySuggestion],
    ) -> List[str]:
        areas: List[str] = []
        if headline_score < 80:
            areas.append("Headline quality needs more focus and specificity")
        if lead_score < 80:
            areas.append("Lead openings should front-load stronger facts")
        if packaging_score < 80 or packaging_suggestions:
            areas.append("Page packaging and visual hierarchy need work")
        if diversity_score < 80 or homogeneity_suggestions:
            areas.append("Headline patterns are becoming too repetitive")
        if not areas:
            areas.append("No major improvement area detected")
        return areas

    def _extract_top_improvements(
        self,
        headline_suggestions: List[HeadlineSuggestion],
        lead_suggestions: List[LeadSuggestion],
        packaging_suggestions: List[PackagingSuggestion],
        homogeneity_suggestions: List[HomogeneitySuggestion],
    ) -> List[ImprovementSuggestion]:
        all_suggestions: List[ImprovementSuggestion] = []

        for suggestion in headline_suggestions:
            all_suggestions.append(
                ImprovementSuggestion(
                    id=suggestion.id,
                    target=ImprovementTarget.HEADLINE,
                    article_id=suggestion.article_id,
                    block_id=None,
                    issue=suggestion.issue_description,
                    issue_type=suggestion.issue_type.value,
                    reason=suggestion.reason,
                    lightweight_suggestion=suggestion.lightweight_suggestion,
                    impact_level=suggestion.impact_level,
                    expected_improvement=suggestion.expected_improvement,
                    original_text=suggestion.headline_text,
                    confidence=suggestion.confidence,
                )
            )

        for suggestion in lead_suggestions:
            all_suggestions.append(
                ImprovementSuggestion(
                    id=suggestion.id,
                    target=ImprovementTarget.LEAD,
                    article_id=suggestion.article_id,
                    block_id=None,
                    issue=suggestion.issue_description,
                    issue_type=suggestion.issue_type.value,
                    reason=suggestion.reason,
                    lightweight_suggestion=suggestion.lightweight_suggestion,
                    impact_level=suggestion.impact_level,
                    expected_improvement=suggestion.expected_improvement,
                    original_text=suggestion.lead_text[:100],
                    confidence=suggestion.confidence,
                )
            )

        for suggestion in packaging_suggestions:
            all_suggestions.append(
                ImprovementSuggestion(
                    id=suggestion.id,
                    target=ImprovementTarget.PACKAGING,
                    article_id=suggestion.article_id,
                    block_id=None,
                    issue=suggestion.issue_description,
                    issue_type=suggestion.issue_type.value,
                    reason=suggestion.reason,
                    lightweight_suggestion=suggestion.lightweight_suggestion,
                    impact_level=suggestion.impact_level,
                    expected_improvement=suggestion.expected_improvement,
                    original_text="",
                    confidence=suggestion.confidence,
                )
            )

        for suggestion in homogeneity_suggestions:
            all_suggestions.append(
                ImprovementSuggestion(
                    id=suggestion.id,
                    target=ImprovementTarget.HOMOGENEITY,
                    article_id=",".join(suggestion.article_ids),
                    block_id=None,
                    issue=suggestion.issue_description,
                    issue_type=suggestion.issue_type,
                    reason=suggestion.reason,
                    lightweight_suggestion=suggestion.lightweight_suggestion,
                    impact_level=suggestion.impact_level,
                    expected_improvement=suggestion.expected_improvement,
                    original_text="",
                    confidence=suggestion.confidence,
                )
            )

        impact_order = {
            ImpactLevel.HIGH: 0,
            ImpactLevel.MEDIUM: 1,
            ImpactLevel.LOW: 2,
        }
        target_order = {
            ImprovementTarget.HEADLINE: 0,
            ImprovementTarget.LEAD: 1,
            ImprovementTarget.PACKAGING: 2,
            ImprovementTarget.HOMOGENEITY: 3,
        }
        aggregated_suggestions = self._aggregate_improvement_suggestions(all_suggestions)
        aggregated_suggestions.sort(
            key=lambda item: (
                impact_order.get(item.impact_level, 3),
                target_order.get(item.target, 4),
                -item.confidence,
            )
        )
        return aggregated_suggestions[:3]

    def _aggregate_improvement_suggestions(
        self, suggestions: List[ImprovementSuggestion]
    ) -> List[ImprovementSuggestion]:
        grouped: Dict[Any, List[ImprovementSuggestion]] = {}

        for suggestion in suggestions:
            key = (
                suggestion.target,
                suggestion.issue_type,
                suggestion.reason,
                suggestion.lightweight_suggestion,
            )
            grouped.setdefault(key, []).append(suggestion)

        aggregated: List[ImprovementSuggestion] = []
        for group in grouped.values():
            if len(group) == 1:
                aggregated.append(group[0])
                continue

            first = group[0]
            article_ids = []
            for item in group:
                if item.article_id and item.article_id not in article_ids:
                    article_ids.append(item.article_id)

            scope_text = f"（涉及{len(article_ids)}篇稿件）" if article_ids else ""
            aggregated.append(
                ImprovementSuggestion(
                    id=first.id,
                    target=first.target,
                    article_id=",".join(article_ids) if article_ids else first.article_id,
                    block_id=first.block_id,
                    issue=f"{first.issue}{scope_text}",
                    issue_type=first.issue_type,
                    reason=first.reason,
                    lightweight_suggestion=first.lightweight_suggestion,
                    impact_level=first.impact_level,
                    expected_improvement=first.expected_improvement,
                    original_text=first.original_text,
                    confidence=max(item.confidence for item in group),
                    metadata={
                        **first.metadata,
                        "article_ids": article_ids,
                        "group_size": len(group),
                    },
                )
            )

        return aggregated
