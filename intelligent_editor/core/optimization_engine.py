"""
Optimization suggestion engine.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.optimization import (
    OptimizationCategory,
    OptimizationPriority,
    OptimizationReport,
    OptimizationSuggestion,
)
from ..models.risk import Risk

logger = logging.getLogger("intelligent_editor")


class OptimizationEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.headline_rules = config.get("headline_rules", {})
        self.layout_rules = config.get("layout_rules", {})
        self.visual_rules = config.get("visual_rules", {})

    def generate_suggestions(
        self,
        structured_data: Dict[str, Any],
        metrics: Dict[str, Any],
        risks: List[Risk],
    ) -> OptimizationReport:
        suggestions: List[OptimizationSuggestion] = []
        suggestions.extend(self._analyze_headlines(structured_data, metrics))
        suggestions.extend(self._analyze_layout_balance(structured_data, metrics))
        suggestions.extend(self._analyze_visual_hierarchy(structured_data, metrics))
        suggestions.extend(self._analyze_readability(structured_data, metrics))
        report = self._create_report(suggestions)
        logger.info("Generated %s optimization suggestions", len(suggestions))
        return report

    def _analyze_headlines(
        self, data: Dict[str, Any], metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []
        blocks_by_id = {block.get("id"): block for block in data.get("blocks", [])}

        for article in data.get("articles", []):
            article_id = article.get("id", "")
            headline = blocks_by_id.get(article.get("headline_block_id"))
            if not headline:
                continue

            headline_text = headline.get("text", "").strip()
            if not headline_text:
                continue

            length_suggestion = self._check_headline_length(headline_text, article_id)
            if length_suggestion:
                suggestions.append(length_suggestion)

            font_size = headline.get("font_size", 0)
            size_suggestion = self._check_headline_font_size(font_size, article_id, headline_text)
            if size_suggestion:
                suggestions.append(size_suggestion)

        return suggestions

    def _analyze_layout_balance(
        self, data: Dict[str, Any], metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []
        left_right = self._check_left_right_balance(data)
        if left_right:
            suggestions.append(left_right)
        return suggestions

    def _analyze_visual_hierarchy(
        self, data: Dict[str, Any], metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []
        font_hierarchy = self._check_font_hierarchy(data)
        if font_hierarchy:
            suggestions.append(font_hierarchy)
        return suggestions

    def _analyze_readability(
        self, data: Dict[str, Any], metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        return []

    def _check_headline_length(
        self, text: str, article_id: str
    ) -> Optional[OptimizationSuggestion]:
        length = len(text)
        max_length = self.headline_rules.get("max_length", 20)
        ideal_length = self.headline_rules.get("ideal_length", 12)
        if length <= max_length:
            return None

        display_text = text if len(text) <= 30 else text[:30] + "..."
        return OptimizationSuggestion(
            id=f"opt_headline_length_{article_id}",
            category=OptimizationCategory.HEADLINE,
            priority=OptimizationPriority.MEDIUM,
            title="Headline too long",
            description=f'Headline "{display_text}" is {length} characters long, above the {max_length} limit.',
            current_state=f"Current length: {length}",
            suggested_state=f"Target length: {ideal_length}-{max_length}",
            benefit="A shorter headline is easier to scan.",
            affected_elements=[f"article_id:{article_id}"],
            confidence=0.8,
            metadata={"headline_text": text, "article_id": article_id},
        )

    def _check_headline_font_size(
        self, font_size: float, article_id: str, text: str
    ) -> Optional[OptimizationSuggestion]:
        if font_size <= 0:
            return None

        min_size = self.headline_rules.get("min_font_size", 14)
        max_size = self.headline_rules.get("max_font_size", 24)
        if font_size >= min_size:
            return None

        display_text = text if len(text) <= 30 else text[:30] + "..."
        return OptimizationSuggestion(
            id=f"opt_headline_size_{article_id}",
            category=OptimizationCategory.HEADLINE,
            priority=OptimizationPriority.MEDIUM,
            title="Headline font too small",
            description=f'Headline "{display_text}" uses {font_size:.1f}pt, below the recommended range.',
            current_state=f"Current size: {font_size:.1f}pt",
            suggested_state=f"Suggested size: {min_size}-{max_size}pt",
            benefit="Stronger visual hierarchy and emphasis.",
            affected_elements=[f"article_id:{article_id}"],
            confidence=0.9,
            metadata={"headline_text": text, "article_id": article_id, "font_size": font_size},
        )

    def _check_left_right_balance(self, data: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        blocks = data.get("blocks", [])
        page_width = data.get("width", 965)
        left_area = 0.0
        right_area = 0.0

        for block in blocks:
            bbox = self._get_bbox(block)
            if not bbox:
                continue
            x0, y0, x1, y1 = bbox
            area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            if x0 < page_width / 2:
                left_area += area
            else:
                right_area += area

        if left_area <= 0 or right_area <= 0:
            return None

        ratio = left_area / right_area
        if 0.83 <= ratio <= 1.2:
            return None

        heavier = "left" if ratio > 1 else "right"
        return OptimizationSuggestion(
            id="opt_layout_balance",
            category=OptimizationCategory.LAYOUT_BALANCE,
            priority=OptimizationPriority.LOW,
            title=f"{heavier.title()} side visually heavier",
            description=f"Left/right content area ratio is {ratio:.2f}:1.",
            current_state=f"Current ratio: {ratio:.2f}:1",
            suggested_state="Aim for a ratio between 0.9:1 and 1.1:1",
            benefit="A more balanced page feels calmer and easier to read.",
            confidence=0.7,
        )

    def _check_font_hierarchy(self, data: Dict[str, Any]) -> Optional[OptimizationSuggestion]:
        font_profile = data.get("font_profile", {})
        headline_stats = font_profile.get("headline", [])
        body_stats = font_profile.get("body", [])
        if len(headline_stats) < 3 or len(body_stats) < 3:
            return None

        headline_avg = headline_stats[2]
        body_avg = body_stats[2]
        if headline_avg <= 0 or body_avg <= 0:
            return None

        ratio = headline_avg / body_avg
        if ratio >= 1.5:
            return None

        return OptimizationSuggestion(
            id="opt_font_hierarchy",
            category=OptimizationCategory.VISUAL_HIERARCHY,
            priority=OptimizationPriority.MEDIUM,
            title="Weak headline/body hierarchy",
            description=f"Headline avg {headline_avg:.1f}pt vs body avg {body_avg:.1f}pt, ratio {ratio:.2f}:1.",
            current_state=f"Current ratio: {ratio:.2f}:1",
            suggested_state="Target ratio: 1.5:1 to 2.0:1",
            benefit="A clearer hierarchy improves reading flow.",
            confidence=0.8,
        )

    def _get_bbox(self, block: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
        if "bbox" in block and isinstance(block["bbox"], list) and len(block["bbox"]) == 4:
            x0, y0, x1, y1 = block["bbox"]
            return float(x0), float(y0), float(x1), float(y1)

        if all(key in block for key in ("x0", "y0", "x1", "y1")):
            return (
                float(block["x0"]),
                float(block["y0"]),
                float(block["x1"]),
                float(block["y1"]),
            )

        return None

    def _create_report(self, suggestions: List[OptimizationSuggestion]) -> OptimizationReport:
        high_count = sum(1 for item in suggestions if item.priority == OptimizationPriority.HIGH)
        medium_count = sum(1 for item in suggestions if item.priority == OptimizationPriority.MEDIUM)
        low_count = sum(1 for item in suggestions if item.priority == OptimizationPriority.LOW)

        headline_suggestions = [
            item for item in suggestions if item.category == OptimizationCategory.HEADLINE
        ]
        layout_suggestions = [
            item for item in suggestions if item.category == OptimizationCategory.LAYOUT_BALANCE
        ]
        visual_suggestions = [
            item for item in suggestions if item.category == OptimizationCategory.VISUAL_HIERARCHY
        ]
        readability_suggestions = [
            item for item in suggestions if item.category == OptimizationCategory.READABILITY
        ]

        optimization_score = max(0, 100 - high_count * 5 - medium_count * 2 - low_count)
        if high_count >= 3 or medium_count >= 5:
            potential = "high"
        elif high_count >= 1 or medium_count >= 2:
            potential = "medium"
        else:
            potential = "low"

        return OptimizationReport(
            suggestions=suggestions,
            total_count=len(suggestions),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            headline_suggestions=headline_suggestions,
            layout_suggestions=layout_suggestions,
            visual_suggestions=visual_suggestions,
            readability_suggestions=readability_suggestions,
            optimization_score=optimization_score,
            optimization_potential=potential,
        )
