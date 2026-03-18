"""
智能审校系统
Intelligent Editor System - 总编辑版面决策支持系统

该系统基于parser_auditor的质量评估结果，进行风险识别和决策支持。
核心目标：3秒内完成判断（是否可以付印/是否存在重大风险/是否需要重点修改）
"""

__version__ = "1.0.0"
__author__ = "黄帮主"

from .models.risk import Risk, Severity
from .models.decision import Decision, DecisionType, RiskLevel

__all__ = [
    "Risk",
    "Severity",
    "Decision",
    "DecisionType",
    "RiskLevel",
]
