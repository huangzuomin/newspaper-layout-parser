"""
解释引擎
Explanation Engine - 生成可解释性说明
"""

from typing import List, Dict, Any
import logging

from ..models.decision import Decision, DecisionType, RiskLevel
from ..models.risk import Risk, Severity
from ..models.report import Score, Explanation

logger = logging.getLogger("intelligent_editor")


class ExplanationEngine:
    """
    解释引擎

    为决策、风险、评分等生成可解释的自然语言说明
    """

    def __init__(self, explanation_config: Dict[str, Any]):
        """
        初始化解释引擎

        Args:
            explanation_config: 从explanation_templates.yaml加载的配置
        """
        self.explanation_config = explanation_config
        self.decision_templates = explanation_config.get('decision_templates', {})
        self.risk_level_templates = explanation_config.get('risk_level_templates', {})
        self.score_templates = explanation_config.get('score_templates', {})
        self.issue_priority_templates = explanation_config.get('issue_priority_templates', {})
        self.confidence_templates = explanation_config.get('confidence_templates', {})
        self.common_issue_explanations = explanation_config.get('common_issue_explanations', {})

        logger.info("ExplanationEngine initialized")

    def generate_explanation(
        self,
        decision: Decision,
        score: Score,
        top_issues: list,
        risks: List[Risk]
    ) -> Explanation:
        """
        生成完整解释

        Args:
            decision: 决策对象
            score: 评分对象
            top_issues: Top问题列表
            risks: 所有风险列表

        Returns:
            Explanation对象
        """
        # 1. 决策解释
        decision_explanation, decision_short = self.explain_decision(decision, score, risks)

        # 2. 风险等级解释
        risk_level_exp, risk_level_name, risk_level_impact = self.explain_risk_level(
            decision.risk_level, risks
        )

        # 3. 评分解释
        score_exp, score_breakdown, grade_exp = self.explain_score(score, risks)

        # 4. 问题优先级解释
        top_issues_exp, priority_reasoning = self.explain_top_issues(top_issues)

        # 5. 置信度解释
        confidence_exp = self.explain_confidence(decision.confidence)

        return Explanation(
            decision_explanation=decision_explanation,
            decision_short=decision_short,
            risk_level_explanation=risk_level_exp,
            risk_level_name=risk_level_name,
            risk_level_impact=risk_level_impact,
            score_explanation=score_exp,
            score_breakdown=score_breakdown,
            grade_explanation=grade_exp,
            top_issues_explanation=top_issues_exp,
            priority_reasoning=priority_reasoning,
            confidence_explanation=confidence_exp
        )

    def explain_decision(
        self,
        decision: Decision,
        score: Score,
        risks: List[Risk]
    ) -> tuple[str, str]:
        """
        解释决策类型

        Args:
            decision: 决策对象
            score: 评分对象
            risks: 风险列表

        Returns:
            (详细解释, 简要说明)
        """
        decision_type = decision.type.value
        template = self.decision_templates.get(decision_type, {})

        # 获取风险统计
        risk_counts = self._count_risks(risks)

        # 生成风险摘要
        risk_summary = self._generate_risk_summary(risk_counts)

        # 详细解释
        detailed = template.get('detailed', '').format(
            grade=score.quality_grade,
            score=score.total_score,
            risk_summary=risk_summary,
            critical_count=risk_counts['critical'],
            high_count=risk_counts['high'],
        )

        # 简要说明
        short = template.get('short', f"{decision_type.upper()}决策")

        return detailed, short

    def explain_risk_level(
        self,
        risk_level: RiskLevel,
        risks: List[Risk]
    ) -> tuple[str, str, str]:
        """
        解释风险等级

        Args:
            risk_level: 风险等级
            risks: 风险列表

        Returns:
            (解释, 名称, 影响)
        """
        level_name = risk_level.name
        template = self.risk_level_templates.get(level_name, {})

        explanation = template.get('description', '')
        name = template.get('name', level_name)
        impact = template.get('impact', '')

        return explanation, name, impact

    def explain_score(self, score: Score, risks: List[Risk]) -> tuple[str, str, str]:
        """
        解释评分

        Args:
            score: 评分对象
            risks: 风险列表

        Returns:
            (评分解释, 评分组成, 等级解释)
        """
        # 评分解释
        intro = self.score_templates.get('breakdown', {}).get('intro', '')

        explanation = intro.format(
            base_score=score.base_score,
            penalty=score.risk_penalty,
            bonus=score.bonus
        )

        # 评分组成
        breakdown = self._generate_score_breakdown(score, risks)

        # 等级解释
        grade_exp = self.score_templates.get('grade_explanations', {}).get(
            score.quality_grade,
            f"{score.quality_grade}级"
        )

        return explanation, breakdown, grade_exp

    def explain_top_issues(self, top_issues: list) -> tuple[str, str]:
        """
        解释问题优先级

        Args:
            top_issues: Top问题列表

        Returns:
            (解释, 优先级原因)
        """
        if not top_issues:
            return "未发现需要重点关注的问题", ""

        intro = self.issue_priority_templates.get('intro', '')
        reasoning_template = self.issue_priority_templates.get('reasoning', '')

        # 生成优先级原因
        highest_severity = top_issues[0].risk.severity.name
        severity_reason = self.issue_priority_templates.get('severity_reasons', {}).get(
            highest_severity,
            ''
        )

        reasoning = reasoning_template.format(
            severity=highest_severity,
            impact_reason=severity_reason
        )

        explanation = f"{intro}\n{reasoning}"

        return explanation, reasoning

    def explain_confidence(self, confidence: float) -> str:
        """
        解释置信度

        Args:
            confidence: 置信度值（0-1）

        Returns:
            置信度解释
        """
        # 确定置信度等级
        if confidence >= 0.8:
            level = 'high'
        elif confidence >= 0.6:
            level = 'medium'
        else:
            level = 'low'

        template = self.confidence_templates.get(level, {})
        explanation = template.get('explanation', f"置信度{confidence:.1%}")

        return explanation

    def _count_risks(self, risks: List[Risk]) -> Dict[str, int]:
        """统计各级风险数量"""
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
        }

        for risk in risks:
            severity_name = risk.severity.name
            if severity_name in counts:
                counts[severity_name] += 1

        return counts

    def _generate_risk_summary(self, risk_counts: Dict[str, int]) -> str:
        """生成风险摘要"""
        parts = []

        if risk_counts['critical'] > 0:
            parts.append(f"{risk_counts['critical']}个重大风险")
        if risk_counts['high'] > 0:
            parts.append(f"{risk_counts['high']}个高风险")
        if risk_counts['medium'] > 0:
            parts.append(f"{risk_counts['medium']}个中等风险")

        if not parts:
            return "无风险"

        return "、".join(parts)

    def _generate_score_breakdown(self, score: Score, risks: List[Risk]) -> str:
        """生成评分组成说明"""
        template = self.score_templates.get('breakdown', {}).get('penalty_detail', '')

        # 统计各级风险数量
        risk_counts = self._count_risks(risks)

        # 获取权重
        weights = {
            'CRITICAL': 30,
            'HIGH': 15,
            'MEDIUM': 5,
            'LOW': 1,
        }

        breakdown = template.format(
            critical_count=risk_counts['critical'],
            critical_weight=weights['CRITICAL'],
            high_count=risk_counts['high'],
            high_weight=weights['HIGH'],
            medium_count=risk_counts['medium'],
            medium_weight=weights['MEDIUM'],
            low_count=risk_counts['low'],
            low_weight=weights['LOW'],
            total_penalty=int(score.risk_penalty),
        )

        # 生成加分说明
        bonus_parts = []
        if score.bonus > 0:
            bonus_reasons = self.score_templates.get('breakdown', {}).get('bonus_reasons', {})
            if risk_counts['critical'] == 0:
                bonus_parts.append(bonus_reasons.get('no_critical', ''))
            if risk_counts['high'] == 0:
                bonus_parts.append(bonus_reasons.get('no_high', ''))
            if len(risks) == 0:
                bonus_parts.append(bonus_reasons.get('perfect', ''))

        if bonus_parts:
            breakdown += f"\n加分：{'. '.join(bonus_parts)}"

        return breakdown
