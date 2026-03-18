"""
报告数据模型
Report Data Model
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Score:
    """
    评分对象

    基于risks生成版面质量评分（0-100）
    """
    total_score: float  # 总分 0-100
    quality_grade: str  # 质量等级：A/B/C/D/F

    # 分数组成
    base_score: float = 0.0  # 基础分（来自parser_auditor）
    risk_penalty: float = 0.0  # 风险扣分
    bonus: float = 0.0  # 加分

    # 分数细项
    breakdown: Dict[str, float] = field(default_factory=dict)

    @property
    def is_passing(self) -> bool:
        """是否及格（≥60分）"""
        return self.total_score >= 60

    @property
    def is_excellent(self) -> bool:
        """是否优秀（≥90分）"""
        return self.total_score >= 90

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'score': round(self.total_score, 1),
            'grade': self.quality_grade,
            'base_score': self.base_score,
            'risk_penalty': self.risk_penalty,
            'bonus': self.bonus,
            'breakdown': self.breakdown,
        }

    def __repr__(self) -> str:
        return f"Score(score={self.total_score:.1f}, grade={self.quality_grade})"


@dataclass
class IntelligentEditorReport:
    """
    智能审校完整报告（4层结构）
    """
    # Level 1: 决策层
    decision: Any  # Decision对象
    risk_level: str  # 风险等级名称

    # Level 2: 评分层
    score: Any  # Score对象
    risk_statistics: Dict[str, int]  # 各级风险数量

    # Level 3: Top问题层
    top_issues: list  # TopIssue列表

    # Level 4: 全部风险
    all_risks: list  # Risk列表

    # 元数据
    processing_time: str  # 处理时间
    parser_confidence: str  # parser_auditor的置信度
    timestamp: str  # 时间戳
    strategy: str = "balanced"  # 决策策略

    def to_dict(self) -> Dict[str, Any]:
        """转换为4层输出字典"""
        return {
            # Level 1: 决策
            'level1_decision': {
                'decision': self.decision.type.value,
                'risk_level': self.decision.risk_level.name,
                'confidence': f"{self.decision.confidence:.1%}",
                'reasoning': self.decision.reasoning,
            },

            # Level 2: 评分
            'level2_score': {
                'total_score': self.score.total_score,
                'grade': self.score.quality_grade,
                'breakdown': self.score.breakdown,
                'risk_statistics': self.risk_statistics,
            },

            # Level 3: Top问题
            'level3_top_issues': [
                issue.to_dict() for issue in self.top_issues
            ],

            # Level 4: 全部风险
            'level4_all_risks': {
                'total_count': len(self.all_risks),
                'risks': [risk.to_dict() for risk in self.all_risks]
            },

            # 元数据
            'metadata': {
                'processing_time': self.processing_time,
                'parser_confidence': self.parser_confidence,
                'timestamp': self.timestamp,
                'strategy': self.strategy,
            }
        }

    def to_summary(self) -> str:
        """生成人类可读摘要"""
        lines = [
            f"决策: {self.decision.type.value.upper()}",
            f"风险等级: {self.decision.risk_level.name}",
            f"评分: {self.score.total_score:.1f}/100 ({self.score.quality_grade})",
            f"置信度: {self.decision.confidence:.1%}",
            "",
            "Top 问题:",
        ]

        for issue in self.top_issues:
            lines.append(f"{issue.rank}. [{issue.risk.severity.name}] {issue.summary}")

        return "\n".join(lines)


@dataclass
class Explanation:
    """
    解释对象

    为决策、风险、评分等生成可解释的自然语言说明
    """
    # 决策解释
    decision_explanation: str = ""  # 决策类型解释
    decision_short: str = ""  # 决策简要说明

    # 风险等级解释
    risk_level_explanation: str = ""  # 风险等级解释
    risk_level_name: str = ""  # 风险等级名称
    risk_level_impact: str = ""  # 风险影响说明

    # 评分解释
    score_explanation: str = ""  # 评分解释
    score_breakdown: str = ""  # 评分组成说明
    grade_explanation: str = ""  # 等级解释

    # 问题优先级解释
    top_issues_explanation: str = ""  # Top问题解释
    priority_reasoning: str = ""  # 优先级原因

    # 置信度解释
    confidence_explanation: str = ""  # 置信度解释

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'decision': {
                'explanation': self.decision_explanation,
                'short': self.decision_short,
            },
            'risk_level': {
                'explanation': self.risk_level_explanation,
                'name': self.risk_level_name,
                'impact': self.risk_level_impact,
            },
            'score': {
                'explanation': self.score_explanation,
                'breakdown': self.score_breakdown,
                'grade_explanation': self.grade_explanation,
            },
            'top_issues': {
                'explanation': self.top_issues_explanation,
                'priority_reasoning': self.priority_reasoning,
            },
            'confidence': {
                'explanation': self.confidence_explanation,
            },
        }

    def __repr__(self) -> str:
        return f"Explanation(decision={self.decision_short}, risk_level={self.risk_level_name})"
