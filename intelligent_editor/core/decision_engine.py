"""
决策引擎
Decision Engine - 基于risks输出决策
"""

from typing import List, Dict, Any
import logging

from ..models.decision import Decision, DecisionType, RiskLevel
from ..models.risk import Risk, Severity
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger("intelligent_editor")


class DecisionEngine:
    """
    决策引擎

    基于risks输出approve/reject/review决策，
    核心是"是否可以付印"。
    """

    def __init__(self, decision_config: Dict[str, Any]):
        """
        初始化决策引擎

        Args:
            decision_config: 从decision_strategy.yaml加载的配置
        """
        self.decision_config = decision_config
        self.default_strategy = decision_config.get('default_strategy', 'balanced')
        self.risk_level_rules = decision_config.get('risk_level_calculation', {})
        self.confidence_rules = decision_config.get('confidence_calculation', {})

        logger.info(f"DecisionEngine initialized with default strategy: {self.default_strategy}")

    def make_decision(
        self,
        risks: List[Risk],
        metrics: Dict,
        strategy: str = None
    ) -> Decision:
        """
        做出版面决策

        Args:
            risks: 风险列表
            metrics: 质量指标（来自parser_auditor）
            strategy: 决策策略（conservative/balanced/aggressive）

        Returns:
            Decision对象
        """
        # 1. 加载策略
        if strategy is None:
            strategy = self.default_strategy

        strategy_config = ConfigLoader.get_strategy_config(
            self.decision_config,
            strategy
        )

        logger.info(f"Using strategy: {strategy}")

        # 2. 统计各级风险数量
        risk_counts = self._count_risks_by_severity(risks)

        # 3. 计算风险等级
        risk_level = self._calculate_risk_level(risk_counts)

        # 4. 应用决策规则
        decision_type = self._apply_decision_rules(
            risk_level,
            risk_counts,
            strategy_config
        )

        # 5. 计算置信度
        confidence = self._calculate_confidence(risks, metrics)

        # 6. 生成决策依据
        reasoning = self._generate_reasoning(
            decision_type,
            risk_level,
            risk_counts,
            strategy_config
        )

        # 7. 提取关键风险
        critical_risks = [r for r in risks if r.severity == Severity.CRITICAL]
        high_risks = [r for r in risks if r.severity == Severity.HIGH]

        # 8. 构建Decision对象
        decision = Decision(
            type=decision_type,
            risk_level=risk_level,
            confidence=confidence,
            reasoning=reasoning,
            critical_risks=critical_risks,
            high_risks=high_risks,
            total_risk_count=len(risks)
        )

        logger.info(f"Decision made: {decision_type.value} (risk_level={risk_level.name}, confidence={confidence:.1%})")

        return decision

    def _count_risks_by_severity(self, risks: List[Risk]) -> Dict[str, int]:
        """
        统计各级风险数量

        Args:
            risks: 风险列表

        Returns:
            各级风险数量字典
        """
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
        }

        for risk in risks:
            severity_name = risk.severity_name.lower()
            if severity_name in counts:
                counts[severity_name] += 1

        return counts

    def _calculate_risk_level(self, risk_counts: Dict[str, int]) -> RiskLevel:
        """
        计算整体风险等级

        规则：
        - CRITICAL: 有任何critical风险
        - HIGH: 有≥2个high风险 或 ≥5个medium风险
        - MEDIUM: 有1个high风险 或 2-4个medium风险
        - LOW: 只有medium/low风险且数量不多

        Args:
            risk_counts: 各级风险数量

        Returns:
            RiskLevel枚举值
        """
        critical_count = risk_counts['critical']
        high_count = risk_counts['high']
        medium_count = risk_counts['medium']

        if critical_count > 0:
            return RiskLevel.CRITICAL
        elif high_count >= 2 or medium_count >= 5:
            return RiskLevel.HIGH
        elif high_count == 1 or (2 <= medium_count <= 4):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _apply_decision_rules(
        self,
        risk_level: RiskLevel,
        risk_counts: Dict[str, int],
        strategy_config: Dict[str, Any]
    ) -> DecisionType:
        """
        应用决策规则

        Args:
            risk_level: 风险等级
            risk_counts: 各级风险数量
            strategy_config: 策略配置

        Returns:
            DecisionType枚举值
        """
        thresholds = strategy_config.get('thresholds', {})

        # 获取各级风险数量
        critical_count = risk_counts['critical']
        high_count = risk_counts['high']
        medium_count = risk_counts['medium']

        # 依次检查approve/review/reject的阈值

        # 检查是否approve
        approve_thresholds = thresholds.get('approve', {})
        if (critical_count <= approve_thresholds.get('max_critical', 0) and
            high_count <= approve_thresholds.get('max_high', 0) and
            medium_count <= approve_thresholds.get('max_medium', 0)):
            return DecisionType.APPROVE

        # 检查是否review
        review_thresholds = thresholds.get('review', {})
        if (critical_count <= review_thresholds.get('max_critical', 0) and
            high_count <= review_thresholds.get('max_high', 0) and
            medium_count <= review_thresholds.get('max_medium', 0)):
            return DecisionType.REVIEW

        # 否则reject
        return DecisionType.REJECT

    def _calculate_confidence(
        self,
        risks: List[Risk],
        metrics: Dict
    ) -> float:
        """
        计算决策置信度

        因素：
        1. parser_auditor的整体confidence
        2. 风险数量（风险越少，置信度越高）

        Args:
            risks: 风险列表
            metrics: 质量指标

        Returns:
            置信度 0-1
        """
        # 基础置信度来自parser_auditor（Phase 1使用固定值）
        base_confidence = 0.8  # 假设parser_auditor的confidence为high

        # 风险数量调整
        risk_count_penalty = min(
            self.confidence_rules.get('max_penalty', 0.2),
            len(risks) * self.confidence_rules.get('risk_count_penalty', 0.02)
        )

        confidence = base_confidence - risk_count_penalty

        return max(0.3, min(1.0, confidence))

    def _generate_reasoning(
        self,
        decision_type: DecisionType,
        risk_level: RiskLevel,
        risk_counts: Dict[str, int],
        strategy_config: Dict[str, Any]
    ) -> str:
        """
        生成决策依据

        Args:
            decision_type: 决策类型
            risk_level: 风险等级
            risk_counts: 各级风险数量
            strategy_config: 策略配置

        Returns:
            决策依据文本
        """
        # 从策略配置获取模板
        templates = strategy_config.get('reasoning_templates', {})

        decision_name = decision_type.value
        template = templates.get(decision_name, '')

        if template:
            # 填充模板
            reasoning = template.format(
                critical_count=risk_counts['critical'],
                high_count=risk_counts['high'],
                medium_count=risk_counts['medium'],
                low_count=risk_counts['low'],
            )
            return reasoning

        # 默认reasoning
        return f"风险等级：{risk_level.name}"
