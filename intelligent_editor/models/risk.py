"""
风险数据模型
Risk Data Model
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Severity(Enum):
    """风险严重等级"""
    CRITICAL = 4  # 会导致付印事故
    HIGH = 3      # 严重影响版面质量
    MEDIUM = 2    # 明显问题，需要关注
    LOW = 1       # 轻微问题，可以忽略


@dataclass
class Risk:
    """
    风险对象

    将parser_auditor的issue/anomaly转化为风险，关注影响而非错误本身。
    """
    id: str  # 风险唯一标识
    type: str  # 风险类型（如missing_headline, narrow_column等）
    severity: Severity  # 风险严重等级
    source: str  # 来源：issue/anomaly/metrics_derived
    description: str  # 风险描述

    # 风险影响范围
    affected_elements: List[str] = field(default_factory=list)  # 受影响的block_id/article_id等
    impact: str = ""  # 对版面的影响说明

    # 置信度和可修复性
    confidence: float = 1.0  # 风险识别置信度 0-1
    is_fixable: bool = False  # 是否可自动修复
    fix_suggestion: Optional[str] = None  # 修复建议

    # 元数据
    source_issue: Optional[Dict] = None  # 原始issue数据
    source_anomaly: Optional[Dict] = None  # 原始anomaly数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据

    @property
    def severity_score(self) -> int:
        """严重程度分数（用于排序）"""
        return self.severity.value

    @property
    def severity_name(self) -> str:
        """严重等级名称"""
        return self.severity.name

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type,
            'severity': self.severity.name,
            'source': self.source,
            'description': self.description,
            'affected_elements': self.affected_elements,
            'impact': self.impact,
            'confidence': self.confidence,
            'is_fixable': self.is_fixable,
            'fix_suggestion': self.fix_suggestion,
        }

    def __repr__(self) -> str:
        return f"Risk(id={self.id}, type={self.type}, severity={self.severity.name})"
