"""
风险识别引擎
Risk Engine - 将issues/anomalies转化为risks
"""

from typing import List, Dict, Any
from collections import defaultdict
import logging

from ..models.risk import Risk, Severity
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger("intelligent_editor")


class RiskEngine:
    """
    风险识别引擎

    将parser_auditor的issues/anomalies转化为risks，
    关注影响而非错误本身。
    """

    def __init__(self, risk_config: Dict[str, Any]):
        """
        初始化风险引擎

        Args:
            risk_config: 从risk_rules.yaml加载的配置
        """
        self.risk_config = risk_config
        self.issue_mappings = risk_config.get('issue_mappings', {})
        self.severity_rules = risk_config.get('severity_rules', {})
        self.aggregation_rules = risk_config.get('aggregation_rules', {})

        logger.info("RiskEngine initialized")

    def identify_risks(
        self,
        issues: List[Dict],
        anomalies: Dict[str, List[Dict]],
        metrics: Dict
    ) -> List[Risk]:
        """
        识别所有风险

        Args:
            issues: HeuristicsChecker的输出
            anomalies: AnomalyDetector的输出
            metrics: MetricsCalculator的输出

        Returns:
            Risk对象列表，按severity排序
        """
        risks = []

        # 1. 从issues转化risks
        risks_from_issues = self._convert_issues_to_risks(issues)
        risks.extend(risks_from_issues)
        logger.info(f"Converted {len(risks_from_issues)} issues to risks")

        # 2. 从anomalies转化risks
        risks_from_anomalies = self._convert_anomalies_to_risks(anomalies)
        risks.extend(risks_from_anomalies)
        logger.info(f"Converted {len(risks_from_anomalies)} anomalies to risks")

        # 3. 从metrics推导risks（隐藏风险）- Phase 2暂不实现
        # risks_from_metrics = self._derive_risks_from_metrics(metrics)
        # risks.extend(risks_from_metrics)

        # 4. 风险聚合和去重
        if self.aggregation_rules.get('same_type_aggregation', False):
            risks = self._aggregate_risks(risks)

        # 5. 按severity排序（从高到低）
        risks.sort(key=lambda r: r.severity_score, reverse=True)

        logger.info(f"Total risks identified: {len(risks)}")
        return risks

    def _convert_issues_to_risks(self, issues: List[Dict]) -> List[Risk]:
        """
        将issues转化为risks

        Args:
            issues: HeuristicsChecker的输出

        Returns:
            Risk对象列表
        """
        risks = []

        for issue in issues:
            # 映射：issue_type → risk_type
            issue_type = issue.get('type', 'unknown')
            risk_type = self.issue_mappings.get(
                issue_type,
                f'{issue_type}_risk'
            )

            # 计算风险等级
            severity = self._calculate_risk_severity_from_issue(issue)

            # 提取受影响的元素
            affected_elements = self._extract_affected_elements(issue)

            # 生成影响说明
            impact = self._generate_impact_description(risk_type, severity)

            # 生成修复建议
            fix_suggestion = self._generate_fix_suggestion(issue_type, issue)

            # 创建Risk对象
            risk = Risk(
                id=f"risk_{len(risks)}",
                type=risk_type,
                severity=severity,
                source='issue',
                description=issue.get('reason', ''),
                affected_elements=affected_elements,
                impact=impact,
                confidence=1.0,  # Phase 1使用固定置信度
                is_fixable=self._is_fixable(issue_type),
                fix_suggestion=fix_suggestion,
                source_issue=issue,
                metadata={
                    'original_issue_type': issue_type,
                    'issue_severity': issue.get('severity', 'low'),
                }
            )

            risks.append(risk)

        return risks

    def _calculate_risk_severity_from_issue(self, issue: Dict) -> Severity:
        """
        从issue计算风险等级

        Args:
            issue: issue字典

        Returns:
            Severity枚举值
        """
        issue_severity = issue.get('severity', 'low')

        # 映射：issue severity → risk severity
        # 保守映射：提升低严重度issue的风险等级
        severity_mapping = {
            'critical': Severity.CRITICAL,
            'high': Severity.HIGH,
            'medium': Severity.MEDIUM,
            'low': Severity.LOW,
        }

        return severity_mapping.get(issue_severity, Severity.LOW)

    def _extract_affected_elements(self, issue: Dict) -> List[str]:
        """
        提取受影响的元素

        Args:
            issue: issue字典

        Returns:
            受影响的元素ID列表
        """
        elements = []

        # 尝试提取各种可能的ID字段
        for key in ['block_id', 'article_id', 'column_id', 'zone']:
            if key in issue:
                elements.append(f"{key}:{issue[key]}")

        return elements

    def _generate_impact_description(self, risk_type: str, severity: Severity) -> str:
        """
        生成影响说明

        Args:
            risk_type: 风险类型
            severity: 风险等级

        Returns:
            影响说明文本
        """
        # 从配置获取描述模板
        severity_name = severity.name.lower()
        severity_rule = self.severity_rules.get(severity_name, {})

        if severity_rule:
            return severity_rule.get('description', '')

        # 默认描述
        return f"{severity_name}风险"

    def _generate_fix_suggestion(self, issue_type: str, issue: Dict) -> str:
        """
        生成修复建议

        Args:
            issue_type: issue类型
            issue: issue字典

        Returns:
            修复建议文本
        """
        # 常见issue类型的修复建议
        suggestions = {
            'missing_headline': '检查article聚类逻辑，确保正确识别headline',
            'too_few_body_blocks': '检查block分类是否正确',
            'narrow_column': '调整分栏检测参数或合并窄栏',
            'too_many_columns': '提高gap_threshold或调整分栏策略',
            'zone_without_headline': '检查该zone的block分类',
            'empty_block': '检查文本提取是否正确',
        }

        return suggestions.get(issue_type, '请人工检查该问题')

    def _is_fixable(self, issue_type: str) -> bool:
        """
        判断是否可自动修复

        Args:
            issue_type: issue类型

        Returns:
            是否可自动修复
        """
        # Phase 1暂不支持自动修复
        return False

    def _aggregate_risks(self, risks: List[Risk]) -> List[Risk]:
        """
        聚合同类型的风险

        Args:
            risks: 风险列表

        Returns:
            聚合后的风险列表
        """
        if not self.aggregation_rules.get('same_type_aggregation', False):
            return risks

        # 按类型分组
        risk_groups = defaultdict(list)
        for risk in risks:
            risk_groups[risk.type].append(risk)

        # 每种类型最多保留max_risks_per_type个风险
        max_per_type = self.aggregation_rules.get('max_risks_per_type', 3)

        aggregated_risks = []
        for risk_type, risk_list in risk_groups.items():
            # 按severity排序，保留前N个
            risk_list.sort(key=lambda r: r.severity_score, reverse=True)
            aggregated_risks.extend(risk_list[:max_per_type])

        return aggregated_risks

    def _convert_anomalies_to_risks(self, anomalies: Dict[str, List[Dict]]) -> List[Risk]:
        """
        将anomalies转化为risks

        Args:
            anomalies: AnomalyDetector的输出（按类别分组的异常字典）

        Returns:
            Risk对象列表
        """
        risks = []

        # 遍历所有类别的anomalies
        for category, anomaly_list in anomalies.items():
            for anomaly in anomaly_list:
                # 获取异常类型
                anomaly_type = anomaly.get('type', 'unknown')

                # 映射：anomaly_type → risk_type
                # 使用与issues相同的映射规则
                risk_type = self.issue_mappings.get(
                    anomaly_type,
                    f'{category}_{anomaly_type}_risk'
                )

                # 计算风险等级
                severity = self._calculate_risk_severity_from_anomaly(anomaly)

                # 提取受影响的元素
                affected_elements = self._extract_affected_elements_from_anomaly(anomaly)

                # 生成影响说明
                impact = self._generate_impact_description(risk_type, severity)

                # 生成修复建议
                fix_suggestion = self._generate_fix_suggestion_from_anomaly(anomaly_type, anomaly)

                # 创建Risk对象
                risk = Risk(
                    id=f"risk_{len(risks)}",
                    type=risk_type,
                    severity=severity,
                    source='anomaly',
                    description=anomaly.get('reason', ''),
                    affected_elements=affected_elements,
                    impact=impact,
                    confidence=1.0,
                    is_fixable=False,
                    fix_suggestion=fix_suggestion,
                    source_anomaly=anomaly,
                    metadata={
                        'original_anomaly_type': anomaly_type,
                        'anomaly_category': category,
                        'anomaly_severity': anomaly.get('severity', 'low'),
                    }
                )

                risks.append(risk)

        return risks

    def _calculate_risk_severity_from_anomaly(self, anomaly: Dict) -> Severity:
        """
        从anomaly计算风险等级

        Args:
            anomaly: anomaly字典

        Returns:
            Severity枚举值
        """
        anomaly_severity = anomaly.get('severity', 'low')

        # 映射：anomaly severity → risk severity
        severity_mapping = {
            'critical': Severity.CRITICAL,
            'high': Severity.HIGH,
            'medium': Severity.MEDIUM,
            'low': Severity.LOW,
        }

        return severity_mapping.get(anomaly_severity, Severity.LOW)

    def _extract_affected_elements_from_anomaly(self, anomaly: Dict) -> List[str]:
        """
        从anomaly提取受影响的元素

        Args:
            anomaly: anomaly字典

        Returns:
            受影响的元素ID列表
        """
        elements = []

        # 尝试提取各种可能的ID字段
        for key in ['block_id', 'article_id', 'column_id', 'zone']:
            if key in anomaly:
                elements.append(f"{key}:{anomaly[key]}")

        return elements

    def _generate_fix_suggestion_from_anomaly(self, anomaly_type: str, anomaly: Dict) -> str:
        """
        为anomaly生成修复建议

        Args:
            anomaly_type: anomaly类型
            anomaly: anomaly字典

        Returns:
            修复建议文本
        """
        # 常见anomaly类型的修复建议
        suggestions = {
            'article_without_headline': '检查article聚类逻辑',
            'article_with_single_body_block': '检查block分类是否正确',
            'oversized_article': '检查是否需要拆分文章',
            'abnormal_column_count': '调整分栏检测参数',
            'extremely_narrow_column': '合并窄栏或调整分栏策略',
            'column_crosses_zones': '使用按zone分栏的模式',
            'zone_without_headline': '检查该zone的block分类',
            'classification_mismatch': '检查block分类逻辑',
            'empty_text_block': '检查文本提取是否正确',
        }

        return suggestions.get(anomaly_type, '请人工检查该异常')
