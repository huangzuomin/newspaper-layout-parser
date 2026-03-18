"""
决策数据模型
Decision Data Model
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

from .risk import Risk


class DecisionType(Enum):
    """决策类型"""
    APPROVE = "approve"   # 可以付印
    REVIEW = "review"     # 需要重点审查
    REJECT = "reject"     # 不能付印


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = 4  # 重大风险
    HIGH = 3      # 高风险
    MEDIUM = 2    # 中等风险
    LOW = 1       # 低风险


@dataclass
class Decision:
    """
    决策对象

    基于risks输出总编辑决策，核心是"是否可以付印"。
    """
    type: DecisionType  # 决策类型
    risk_level: RiskLevel  # 整体风险等级
    confidence: float  # 决策置信度 0-1
    reasoning: str  # 决策依据（自然语言）

    # 风险汇总
    critical_risks: List[Risk] = field(default_factory=list)  # CRITICAL风险列表
    high_risks: List[Risk] = field(default_factory=list)  # HIGH风险列表
    total_risk_count: int = 0  # 总风险数量

    # 时间戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def can_print(self) -> bool:
        """是否可以付印"""
        return self.type == DecisionType.APPROVE

    @property
    def needs_attention(self) -> bool:
        """是否需要重点关注"""
        return self.type in [DecisionType.REVIEW, DecisionType.REJECT]

    @property
    def critical_count(self) -> int:
        """CRITICAL风险数量"""
        return len(self.critical_risks)

    @property
    def high_count(self) -> int:
        """HIGH风险数量"""
        return len(self.high_risks)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'decision': self.type.value,
            'risk_level': self.risk_level.name,
            'confidence': f"{self.confidence:.1%}",
            'reasoning': self.reasoning,
            'critical_risk_count': self.critical_count,
            'high_risk_count': self.high_count,
            'total_risk_count': self.total_risk_count,
            'timestamp': self.timestamp,
        }

    def __repr__(self) -> str:
        return f"Decision(type={self.type.value}, risk_level={self.risk_level.name}, confidence={self.confidence:.1%})"
