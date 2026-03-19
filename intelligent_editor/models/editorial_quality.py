"""
编辑质量数据模型
Editorial Quality Data Models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


# ═══════════════════════════════════════════════════════════
# 枚举类型
# ═══════════════════════════════════════════════════════════

class ImprovementTarget(Enum):
    """改进目标类型"""
    HEADLINE = "headline"
    LEAD = "lead"
    PACKAGING = "packaging"
    HOMOGENEITY = "homogeneity"  # 同质化
    VISUAL = "visual"


class HeadlineIssueType(Enum):
    """标题问题类型"""
    TOO_LONG = "too_long"
    TOO_GENERIC = "too_generic"
    MEETING_STYLE_HEAVY = "meeting_style_heavy"
    REPETITIVE_WITH_KICKER = "repetitive_with_kicker"
    WEAK_FOCUS = "weak_focus"


class LeadIssueType(Enum):
    """导语问题类型"""
    SLOW_START = "slow_start"
    ABSTRACT_OPENING = "abstract_opening"
    REPEATED_WITH_HEADLINE = "repeated_with_headline"
    INSUFFICIENT_NEWS_VALUE_FRONTLOADING = "insufficient_news_value_frontloading"


class PackagingIssueType(Enum):
    """包装问题类型"""
    PHOTO_WEAK_TEXT = "photo_weak_text"  # 图强文弱
    PHOTO_TEXT_DISCONNECTED = "photo_text_disconnected"  # 图文脱节
    LOW_VISUAL_HIERARCHY = "low_visual_hierarchy"  # 视觉层次不足


class ImpactLevel(Enum):
    """影响程度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ═══════════════════════════════════════════════════════════
# 标题建议
# ═══════════════════════════════════════════════════════════

@dataclass
class HeadlineSuggestion:
    """标题改进建议"""
    id: str
    article_id: str
    headline_text: str

    # 问题识别
    issue_type: HeadlineIssueType
    issue_description: str

    # 分析
    reason: str  # 为什么这是问题
    current_approach: str  # 当前做法的问题

    # 改进建议
    lightweight_suggestion: str  # 轻改建议

    # 影响评估
    impact_level: ImpactLevel
    expected_improvement: str  # 预期改进效果

    # 可选字段（有默认值）
    alternative_headlines: List[str] = field(default_factory=list)  # 可选的替代标题

    # 元数据
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "article_id": self.article_id,
            "headline_text": self.headline_text,
            "issue_type": self.issue_type.value,
            "issue_description": self.issue_description,
            "reason": self.reason,
            "current_approach": self.current_approach,
            "lightweight_suggestion": self.lightweight_suggestion,
            "alternative_headlines": self.alternative_headlines,
            "impact_level": self.impact_level.value,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════
# 导语建议
# ═══════════════════════════════════════════════════════════

@dataclass
class LeadSuggestion:
    """导语改进建议"""
    id: str
    article_id: str
    lead_text: str

    # 问题识别
    issue_type: LeadIssueType
    issue_description: str

    # 分析
    reason: str
    current_approach: str

    # 改进建议
    lightweight_suggestion: str

    # 影响评估
    impact_level: ImpactLevel
    expected_improvement: str

    # 可选字段（有默认值）
    revised_lead_example: str = ""  # 改写示例

    # 元数据
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "article_id": self.article_id,
            "lead_text": self.lead_text[:100] + "..." if len(self.lead_text) > 100 else self.lead_text,
            "issue_type": self.issue_type.value,
            "issue_description": self.issue_description,
            "reason": self.reason,
            "current_approach": self.current_approach,
            "lightweight_suggestion": self.lightweight_suggestion,
            "revised_lead_example": self.revised_lead_example,
            "impact_level": self.impact_level.value,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════
# 包装建议
# ═══════════════════════════════════════════════════════════

@dataclass
class PackagingSuggestion:
    """包装改进建议"""
    id: str
    article_id: str
    issue_type: PackagingIssueType
    issue_description: str

    # 分析
    reason: str
    current_state: str

    # 改进建议
    lightweight_suggestion: str

    # 影响评估
    impact_level: ImpactLevel
    expected_improvement: str

    # 元数据
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "article_id": self.article_id,
            "issue_type": self.issue_type.value,
            "issue_description": self.issue_description,
            "reason": self.reason,
            "current_state": self.current_state,
            "lightweight_suggestion": self.lightweight_suggestion,
            "impact_level": self.impact_level.value,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════
# 同质化建议
# ═══════════════════════════════════════════════════════════

@dataclass
class HomogeneitySuggestion:
    """同质化改进建议"""
    id: str
    article_ids: List[str]
    issue_type: str  # "expression_homogeneity" or "structure_homogeneity"
    issue_description: str

    # 分析
    reason: str
    similarity_analysis: str  # 相似性分析

    # 改进建议
    lightweight_suggestion: str

    # 影响评估
    impact_level: ImpactLevel
    expected_improvement: str

    # 元数据
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "article_ids": self.article_ids,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "reason": self.reason,
            "similarity_analysis": self.similarity_analysis,
            "lightweight_suggestion": self.lightweight_suggestion,
            "impact_level": self.impact_level.value,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════
# 综合改进建议
# ═══════════════════════════════════════════════════════════

@dataclass
class ImprovementSuggestion:
    """综合改进建议（统一接口）"""
    id: str
    target: ImprovementTarget
    article_id: Optional[str]
    block_id: Optional[str]

    # 问题识别
    issue: str
    issue_type: str

    # 分析
    reason: str

    # 改进建议
    lightweight_suggestion: str

    # 影响评估
    impact_level: ImpactLevel
    expected_improvement: str

    # 原文片段
    original_text: str = ""

    # 元数据
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "target": self.target.value,
            "article_id": self.article_id,
            "block_id": self.block_id,
            "issue": self.issue,
            "issue_type": self.issue_type,
            "reason": self.reason,
            "lightweight_suggestion": self.lightweight_suggestion,
            "impact_level": self.impact_level.value,
            "expected_improvement": self.expected_improvement,
            "original_text": self.original_text[:100] + "..." if len(self.original_text) > 100 else self.original_text,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════
# 版面编辑质量评估
# ═══════════════════════════════════════════════════════════

@dataclass
class EditorialQualityAssessment:
    """版面编辑质量评估"""
    overall_score: float  # 0-100
    overall_grade: str  # A/B/C/D

    # 总编辑视角的判断
    overall_editorial_assessment: str  # 一句话评价

    # 强项
    strengths: List[str]

    # 改进空间
    improvement_areas: List[str]

    # 关键指标
    headline_quality_score: float
    lead_quality_score: float
    packaging_quality_score: float
    diversity_score: float  # 多样性（避免同质化）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "overall_editorial_assessment": self.overall_editorial_assessment,
            "strengths": self.strengths,
            "improvement_areas": self.improvement_areas,
            "headline_quality_score": self.headline_quality_score,
            "lead_quality_score": self.lead_quality_score,
            "packaging_quality_score": self.packaging_quality_score,
            "diversity_score": self.diversity_score
        }


# ═══════════════════════════════════════════════════════════
# 品质提升报告
# ═══════════════════════════════════════════════════════════

@dataclass
class QualityImprovementReport:
    """品质提升报告"""

    # 编辑质量评估
    assessment: EditorialQualityAssessment

    # Top 3 最值得优化的点
    top_improvement_points: List[ImprovementSuggestion]

    # 分类建议
    headline_suggestions: List[HeadlineSuggestion]
    lead_suggestions: List[LeadSuggestion]
    packaging_suggestions: List[PackagingSuggestion]
    homogeneity_suggestions: List[HomogeneitySuggestion]

    # 统计
    total_suggestions: int
    high_impact_count: int
    medium_impact_count: int
    low_impact_count: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "assessment": self.assessment.to_dict(),
            "top_improvement_points": [s.to_dict() for s in self.top_improvement_points],
            "headline_suggestions": [s.to_dict() for s in self.headline_suggestions],
            "lead_suggestions": [s.to_dict() for s in self.lead_suggestions],
            "packaging_suggestions": [s.to_dict() for s in self.packaging_suggestions],
            "homogeneity_suggestions": [s.to_dict() for s in self.homogeneity_suggestions],
            "total_suggestions": self.total_suggestions,
            "high_impact_count": self.high_impact_count,
            "medium_impact_count": self.medium_impact_count,
            "low_impact_count": self.low_impact_count
        }


# ═══════════════════════════════════════════════════════════
# 发布决策（原有风险决策）
# ═══════════════════════════════════════════════════════════

@dataclass
class PublicationDecision:
    """发布决策"""
    decision: str  # approve/review/reject
    risk_level: str
    confidence: float

    # 阻塞性问题（必须解决才能发布）
    blocking_issues: List[str]

    # 决策依据
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "decision": self.decision,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "blocking_issues": self.blocking_issues,
            "reasoning": self.reasoning
        }


# ═══════════════════════════════════════════════════════════
# 双通道输出报告
# ═══════════════════════════════════════════════════════════

@dataclass
class DualChannelReport:
    """双通道输出报告"""

    # 通道A：发布决策
    publication_decision: PublicationDecision

    # 通道B：品质提升
    quality_improvement: QualityImprovementReport

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "publication_decision": self.publication_decision.to_dict(),
            "quality_improvement": self.quality_improvement.to_dict(),
            "metadata": self.metadata
        }
