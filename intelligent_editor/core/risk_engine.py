"""
Risk engine for converting parser auditor issues and anomalies into normalized risks.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from ..models.risk import Risk, Severity

logger = logging.getLogger("intelligent_editor")


class RiskEngine:
    """Convert parser_auditor outputs into normalized risks."""

    def __init__(self, risk_config: Dict[str, Any]):
        self.risk_config = risk_config
        self.issue_mappings = risk_config.get("issue_mappings", {})
        self.severity_rules = risk_config.get("severity_rules", {})
        self.aggregation_rules = risk_config.get("aggregation_rules", {})
        self._risk_counter = 0
        logger.info("RiskEngine initialized")

    def identify_risks(
        self,
        issues: List[Dict],
        anomalies: Dict[str, List[Dict]],
        metrics: Dict,
    ) -> List[Risk]:
        del metrics  # Reserved for future derived risk logic.

        self._risk_counter = 0
        risks: List[Risk] = []

        risks_from_issues = self._convert_issues_to_risks(issues)
        risks.extend(risks_from_issues)
        logger.info("Converted %s issues to risks", len(risks_from_issues))

        risks_from_anomalies = self._convert_anomalies_to_risks(anomalies)
        risks.extend(risks_from_anomalies)
        logger.info("Converted %s anomalies to risks", len(risks_from_anomalies))

        if self.aggregation_rules.get("same_type_aggregation", False):
            risks = self._aggregate_risks(risks)

        risks.sort(key=lambda risk: risk.severity_score, reverse=True)
        logger.info("Total risks identified: %s", len(risks))
        return risks

    def _next_risk_id(self) -> str:
        risk_id = f"risk_{self._risk_counter}"
        self._risk_counter += 1
        return risk_id

    def _convert_issues_to_risks(self, issues: List[Dict]) -> List[Risk]:
        risks = []
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            risk_type = self._normalize_risk_type(issue_type)
            severity = self._calculate_risk_severity(issue.get("severity", "low"))
            risk = Risk(
                id=self._next_risk_id(),
                type=risk_type,
                severity=severity,
                source="issue",
                description=issue.get("reason", ""),
                affected_elements=self._extract_affected_elements(issue),
                impact=self._generate_impact_description(severity),
                confidence=1.0,
                is_fixable=self._is_fixable(issue_type),
                fix_suggestion=self._generate_fix_suggestion(issue_type),
                source_issue=issue,
                metadata={
                    "original_issue_type": issue_type,
                    "issue_severity": issue.get("severity", "low"),
                },
            )
            risks.append(risk)
        return risks

    def _convert_anomalies_to_risks(self, anomalies: Dict[str, List[Dict]]) -> List[Risk]:
        risks = []
        for category, anomaly_list in anomalies.items():
            for anomaly in anomaly_list:
                anomaly_type = anomaly.get("type", "unknown")
                risk_type = self._normalize_risk_type(anomaly_type, category)
                severity = self._calculate_risk_severity(anomaly.get("severity", "low"))
                risk = Risk(
                    id=self._next_risk_id(),
                    type=risk_type,
                    severity=severity,
                    source="anomaly",
                    description=anomaly.get("reason", ""),
                    affected_elements=self._extract_affected_elements(anomaly),
                    impact=self._generate_impact_description(severity),
                    confidence=1.0,
                    is_fixable=False,
                    fix_suggestion=self._generate_fix_suggestion_from_anomaly(anomaly_type),
                    source_anomaly=anomaly,
                    metadata={
                        "original_anomaly_type": anomaly_type,
                        "anomaly_category": category,
                        "anomaly_severity": anomaly.get("severity", "low"),
                    },
                )
                risks.append(risk)
        return risks

    def _normalize_risk_type(self, source_type: str, category: str | None = None) -> str:
        if source_type in self.issue_mappings:
            return self.issue_mappings[source_type]

        if source_type.endswith("_risk"):
            return source_type

        aliases = {
            "article_without_headline": "critical_article_risk",
            "article_with_single_body_block": "high_article_risk",
            "oversized_article": "low_article_risk",
            "abnormal_column_count": "high_layout_risk",
            "extremely_narrow_column": "medium_layout_risk",
            "column_crosses_zones": "high_layout_risk",
            "section_label_overfire": "medium_global_risk",
            "empty_text_block": "low_block_risk",
        }
        if source_type in aliases:
            return aliases[source_type]

        if category:
            return f"{category}_{source_type}_risk"
        return f"{source_type}_risk"

    def _calculate_risk_severity(self, level: str) -> Severity:
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        return mapping.get(level, Severity.LOW)

    def _extract_affected_elements(self, item: Dict) -> List[str]:
        elements = []
        for key in ["block_id", "article_id", "column_id", "zone"]:
            if key in item:
                elements.append(f"{key}:{item[key]}")
        return elements

    def _generate_impact_description(self, severity: Severity) -> str:
        severity_rule = self.severity_rules.get(severity.name.lower(), {})
        if severity_rule:
            return severity_rule.get("description", "")
        return f"{severity.name.lower()} risk"

    def _generate_fix_suggestion(self, issue_type: str) -> str:
        suggestions = {
            "missing_headline": "检查article聚类逻辑，确保正确识别headline",
            "too_few_body_blocks": "检查block分类是否正确",
            "narrow_column": "调整分栏检测参数或合并窄栏",
            "too_many_columns": "提高gap_threshold或调整分栏策略",
            "zone_without_headline": "检查该zone的block分类",
            "empty_block": "检查文本提取是否正确",
        }
        return suggestions.get(issue_type, "请人工检查该问题")

    def _generate_fix_suggestion_from_anomaly(self, anomaly_type: str) -> str:
        suggestions = {
            "article_without_headline": "检查article聚类逻辑",
            "article_with_single_body_block": "检查block分类是否正确",
            "oversized_article": "检查是否需要拆分文章",
            "abnormal_column_count": "调整分栏检测参数",
            "extremely_narrow_column": "合并窄栏或调整分栏策略",
            "column_crosses_zones": "使用按zone分栏的模式",
            "zone_without_headline": "检查该zone的block分类",
            "classification_mismatch": "检查block分类逻辑",
            "empty_text_block": "检查文本提取是否正确",
            "section_label_overfire": "请人工检查该问题",
        }
        return suggestions.get(anomaly_type, "请人工检查该异常")

    def _is_fixable(self, issue_type: str) -> bool:
        del issue_type
        return False

    def _aggregate_risks(self, risks: List[Risk]) -> List[Risk]:
        risk_groups: Dict[str, List[Risk]] = defaultdict(list)
        for risk in risks:
            risk_groups[risk.type].append(risk)

        max_per_type = self.aggregation_rules.get("max_risks_per_type", 3)
        aggregated_risks: List[Risk] = []
        for risk_list in risk_groups.values():
            risk_list.sort(key=lambda risk: risk.severity_score, reverse=True)
            aggregated_risks.extend(risk_list[:max_per_type])
        return aggregated_risks
