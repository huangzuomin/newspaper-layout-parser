"""
评分引擎
Scoring Engine - 生成版面质量评分
"""

from typing import List, Dict, Any
import logging

from ..models.risk import Risk, Severity
from ..models.report import Score

logger = logging.getLogger("intelligent_editor")


class ScoringEngine:
    """
    评分引擎

    基于risks生成版面质量评分（0-100）
    """

    def __init__(self, scoring_config: Dict[str, Any]):
        """
        初始化评分引擎

        Args:
            scoring_config: 从scoring_weights.yaml加载的配置
        """
        self.scoring_config = scoring_config
        self.risk_weights = scoring_config.get('risk_weights', {})
        self.max_penalty = scoring_config.get('max_penalty', 50)
        self.bonus_rules = scoring_config.get('bonus_rules', {})
        self.grade_thresholds = scoring_config.get('grade_thresholds', {})

        logger.info("ScoringEngine initialized")

    def calculate_score(
        self,
        risks: List[Risk],
        metrics: Dict
    ) -> Score:
        """
        计算版面质量评分

        Args:
            risks: 风险列表
            metrics: 质量指标（来自parser_auditor）

        Returns:
            Score对象
        """
        # 1. 基础分（来自parser_auditor）
        base_score = metrics.get('score', 85)  # 默认85分

        # 2. 风险扣分
        risk_penalty = self._calculate_risk_penalty(risks)

        # 3. 加分项（无风险时的奖励）
        bonus = self._calculate_bonus(risks)

        # 4. 最终分数
        total_score = max(0, min(100, base_score - risk_penalty + bonus))

        # 5. 分数细项
        breakdown = self._generate_breakdown(
            base_score,
            risk_penalty,
            bonus,
            risks
        )

        # 6. 质量等级
        quality_grade = self._determine_grade(total_score)

        logger.info(
            f"Score calculated: {total_score:.1f} "
            f"(base={base_score}, penalty={risk_penalty}, bonus={bonus})"
        )

        return Score(
            total_score=total_score,
            quality_grade=quality_grade,
            base_score=base_score,
            risk_penalty=risk_penalty,
            bonus=bonus,
            breakdown=breakdown
        )

    def _calculate_risk_penalty(self, risks: List[Risk]) -> float:
        """
        计算风险扣分

        规则：
        - CRITICAL: 每个-30分
        - HIGH: 每个-15分
        - MEDIUM: 每个-5分
        - LOW: 每个-1分

        Args:
            risks: 风险列表

        Returns:
            扣分值
        """
        penalty = 0.0

        for risk in risks:
            severity_name = risk.severity.name
            weight = self.risk_weights.get(severity_name, 0)
            penalty += weight

        # 设置扣分上限
        penalty = min(penalty, self.max_penalty)

        return penalty

    def _calculate_bonus(self, risks: List[Risk]) -> float:
        """
        计算加分

        规则：
        - 无CRITICAL风险: +5分
        - 无HIGH风险: +3分
        - 无任何风险: +10分

        Args:
            risks: 风险列表

        Returns:
            加分值
        """
        bonus = 0.0

        # 统计各级风险数量
        critical_count = sum(1 for r in risks if r.severity == Severity.CRITICAL)
        high_count = sum(1 for r in risks if r.severity == Severity.HIGH)

        # 无CRITICAL风险奖励
        if critical_count == 0:
            bonus += self.bonus_rules.get('no_critical', 5)

        # 无HIGH风险奖励
        if high_count == 0:
            bonus += self.bonus_rules.get('no_high', 3)

        # 完美无风险奖励
        if len(risks) == 0:
            bonus = self.bonus_rules.get('perfect', 10)

        return bonus

    def _determine_grade(self, total_score: float) -> str:
        """
        确定质量等级

        规则：
        - A: 90-100分
        - B: 80-89分
        - C: 70-79分
        - D: 60-69分
        - F: 0-59分

        Args:
            total_score: 总分

        Returns:
            质量等级（A/B/C/D/F）
        """
        if total_score >= self.grade_thresholds.get('A', 90):
            return 'A'
        elif total_score >= self.grade_thresholds.get('B', 80):
            return 'B'
        elif total_score >= self.grade_thresholds.get('C', 70):
            return 'C'
        elif total_score >= self.grade_thresholds.get('D', 60):
            return 'D'
        else:
            return 'F'

    def _generate_breakdown(
        self,
        base_score: float,
        risk_penalty: float,
        bonus: float,
        risks: List[Risk]
    ) -> Dict[str, float]:
        """
        生成分数细项

        Args:
            base_score: 基础分
            risk_penalty: 风险扣分
            bonus: 加分
            risks: 风险列表

        Returns:
            分数细项字典
        """
        # 统计各级风险扣分
        critical_penalty = sum(
            self.risk_weights.get('CRITICAL', 30)
            for r in risks if r.severity == Severity.CRITICAL
        )
        high_penalty = sum(
            self.risk_weights.get('HIGH', 15)
            for r in risks if r.severity == Severity.HIGH
        )
        medium_penalty = sum(
            self.risk_weights.get('MEDIUM', 5)
            for r in risks if r.severity == Severity.MEDIUM
        )
        low_penalty = sum(
            self.risk_weights.get('LOW', 1)
            for r in risks if r.severity == Severity.LOW
        )

        breakdown = {
            'base_score': base_score,
            'critical_penalty': critical_penalty,
            'high_penalty': high_penalty,
            'medium_penalty': medium_penalty,
            'low_penalty': low_penalty,
            'total_penalty': risk_penalty,
            'bonus': bonus,
        }

        return breakdown
