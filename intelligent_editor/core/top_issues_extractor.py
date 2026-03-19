"""
Top issue extraction with blocker-aware filtering and editor-friendly phrasing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from ..models.decision import Decision, DecisionType
from ..models.risk import Risk, Severity

logger = logging.getLogger("intelligent_editor")


@dataclass
class TopIssue:
    """Compact issue item shown in publication-facing reports."""

    rank: int
    risk: Risk
    summary: str
    action_needed: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "severity": self.risk.severity.name,
            "summary": self.summary,
            "action_needed": self.action_needed,
            "affected_elements": self.risk.affected_elements,
        }


class TopIssuesExtractor:
    """Pick the most important publication issues from the risk list."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.max_issues = self.config.get("max_issues", 3)
        logger.info(
            "TopIssuesExtractor initialized with max_issues=%s", self.max_issues
        )

    def extract_top_issues(
        self, risks: List[Risk], decision: Decision
    ) -> List[TopIssue]:
        if not risks:
            logger.info("No risks to extract")
            return []

        filtered_risks = self._filter_risks(risks, decision)
        deduplicated_risks = self._deduplicate_risks(filtered_risks)
        sorted_risks = self._sort_risks(deduplicated_risks)
        top_risks = sorted_risks[: self.max_issues]

        top_issues = [
            TopIssue(
                rank=index + 1,
                risk=risk,
                summary=self._generate_summary(risk),
                action_needed=self._suggest_action(risk),
            )
            for index, risk in enumerate(top_risks)
        ]

        logger.info(
            "Extracted %s top issues from %s filtered risks",
            len(top_issues),
            len(filtered_risks),
        )
        return top_issues

    def _filter_risks(self, risks: List[Risk], decision: Decision) -> List[Risk]:
        severity_preferences = {
            DecisionType.REJECT: [
                [Severity.CRITICAL, Severity.HIGH],
                [Severity.MEDIUM],
                [Severity.LOW],
            ],
            DecisionType.REVIEW: [
                [Severity.CRITICAL, Severity.HIGH],
                [Severity.MEDIUM],
            ],
            DecisionType.APPROVE: [
                [Severity.HIGH, Severity.MEDIUM],
                [Severity.LOW],
            ],
        }

        for severity_group in severity_preferences.get(decision.type, [[Severity.HIGH]]):
            matched = [risk for risk in risks if risk.severity in severity_group]
            if matched:
                logger.info(
                    "Top issue filter kept %s risks for decision %s with severities %s",
                    len(matched),
                    decision.type.value,
                    [severity.name for severity in severity_group],
                )
                return matched

        logger.info("Top issue filter fell back to all risks")
        return list(risks)

    def _deduplicate_risks(self, risks: List[Risk]) -> List[Risk]:
        unique_risks: List[Risk] = []
        seen_keys = set()

        for risk in risks:
            key = self._risk_group_key(risk)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique_risks.append(risk)

        return unique_risks

    def _risk_group_key(self, risk: Risk):
        primary_element = risk.affected_elements[0] if risk.affected_elements else ""
        canonical_type = self._canonical_type_group(risk.type)
        return (risk.severity.name, primary_element, canonical_type)

    def _canonical_type_group(self, risk_type: str) -> str:
        if "article" in risk_type and "headline" in risk_type:
            return "article_headline"
        if "layout" in risk_type or "column" in risk_type:
            return "layout"
        if "block" in risk_type:
            return "block"
        if "global" in risk_type:
            return "global"
        return risk_type

    def _sort_risks(self, risks: List[Risk]) -> List[Risk]:
        def sort_key(risk: Risk):
            return (-risk.severity_score, -len(risk.affected_elements), -risk.confidence)

        return sorted(risks, key=sort_key)

    def _generate_summary(self, risk: Risk) -> str:
        primary_element = (
            self._simplify_element_label(risk.affected_elements[0])
            if risk.affected_elements
            else ""
        )

        if risk.type == "critical_article_risk":
            return (
                f"文章 {primary_element} 缺少标题"
                if primary_element
                else "存在文章缺少标题"
            )

        if risk.type == "high_layout_risk":
            if "Column " in risk.description and "crosses" in risk.description:
                return f"栏位 {primary_element or '未命名栏'} 跨区域混排"
            if "Too many columns" in risk.description:
                count = self._extract_number(risk.description)
                return f"分栏数异常偏多，当前约 {count} 栏" if count else "分栏数异常偏多"

        if risk.type == "medium_layout_risk":
            return (
                f"区域 {primary_element} 缺少标题引导"
                if primary_element
                else "存在区域缺少标题引导"
            )

        if risk.type == "high_article_risk":
            return (
                f"文章 {primary_element} 正文块过少"
                if primary_element
                else "存在文章正文块过少"
            )

        if risk.type == "medium_global_risk":
            return "栏目标记偏多，版面层级可能混乱"

        if risk.type == "low_block_risk":
            return (
                f"块 {primary_element} 分类结果不稳定"
                if primary_element
                else "存在版面块分类不稳定"
            )

        if primary_element:
            return f"{primary_element}: {self._compact_text(risk.description, 20)}"
        if risk.description:
            return self._compact_text(risk.description, 20)
        return self._compact_text(risk.type.replace("_", " "), 20)

    def _simplify_element_label(self, element: str) -> str:
        return element.split(":", 1)[1] if ":" in element else element

    def _compact_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    def _suggest_action(self, risk: Risk) -> str:
        action_templates = {
            "critical_article_risk": "补齐标题并复核文章归类",
            "high_layout_risk": "优先调整分栏与区域边界",
            "medium_layout_risk": "补强该区标题或导读层级",
            "high_article_risk": "补充正文或复核合并拆分",
            "medium_global_risk": "压缩栏目标记并人工复核",
            "low_block_risk": "复核该块的文本分类结果",
        }

        if risk.type in action_templates:
            return action_templates[risk.type]
        if risk.fix_suggestion:
            return self._compact_text(risk.fix_suggestion, 20)
        return "请人工复核"

    def _extract_number(self, text: str) -> str:
        digits = []
        for char in text:
            if char.isdigit():
                digits.append(char)
            elif digits:
                break
        return "".join(digits)
