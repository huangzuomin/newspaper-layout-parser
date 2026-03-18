"""
优化建议数据模型
Optimization Suggestion Data Models
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class OptimizationCategory(Enum):
    """优化建议类别"""
    HEADLINE = "headline"           # 标题优化
    LAYOUT_BALANCE = "layout_balance"  # 版面平衡
    VISUAL_HIERARCHY = "visual_hierarchy"  # 视觉层次
    READABILITY = "readability"     # 可读性
    COLUMN_STRUCTURE = "column_structure"  # 分栏结构
    WHITE_SPACE = "white_space"     # 留白利用
    IMAGE_PLACEMENT = "image_placement"  # 图文搭配


class OptimizationPriority(Enum):
    """优化建议优先级"""
    HIGH = "high"        # 强烈建议优化
    MEDIUM = "medium"    # 建议优化
    LOW = "low"          # 可选优化


@dataclass
class OptimizationSuggestion:
    """
    优化建议

    与Risk不同，Optimization是可选的改进建议，
    不影响付印决策，但能提升版面质量。
    """
    id: str
    category: OptimizationCategory
    priority: OptimizationPriority
    title: str  # 建议标题（简短）
    description: str  # 详细描述
    current_state: str  # 当前状态
    suggested_state: str  # 建议状态
    benefit: str  # 优化后的好处
    affected_elements: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 建议的置信度
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外信息（如标题文本）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'category': self.category.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'current_state': self.current_state,
            'suggested_state': self.suggested_state,
            'benefit': self.benefit,
            'affected_elements': self.affected_elements,
            'confidence': self.confidence,
            'metadata': self.metadata  # 包含真实标题文本等
        }


@dataclass
class OptimizationReport:
    """
    优化建议报告

    包含所有优化建议的汇总
    """
    suggestions: List[OptimizationSuggestion]
    total_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int

    # 按类别分组的建议
    headline_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    layout_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    visual_suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    readability_suggestions: List[OptimizationSuggestion] = field(default_factory=list)

    # 总体优化评分
    optimization_score: float = 0.0  # 0-100
    optimization_potential: str = ""  # "高"/"中"/"低"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_count': self.total_count,
            'high_priority_count': self.high_priority_count,
            'medium_priority_count': self.medium_priority_count,
            'low_priority_count': self.low_priority_count,
            'suggestions': [s.to_dict() for s in self.suggestions],
            'optimization_score': self.optimization_score,
            'optimization_potential': self.optimization_potential,
            'summary': {
                'headline': len(self.headline_suggestions),
                'layout': len(self.layout_suggestions),
                'visual': len(self.visual_suggestions),
                'readability': len(self.readability_suggestions)
            }
        }
