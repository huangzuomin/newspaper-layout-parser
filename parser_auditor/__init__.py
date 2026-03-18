"""
Parser Auditor - PDF解析结果质量评估模块
Parser Auditor Module for Quality Assessment of PDF Parsing Results

该模块对parser输出的structured.json进行质量评估，
包括指标计算、异常检测、评分系统等。
"""

__version__ = "0.1.0"
__author__ = "Claude Code"

from .metrics import MetricsCalculator
from .heuristics import HeuristicsChecker
from .anomaly import AnomalyDetector
from .report import ReportGenerator

__all__ = [
    "MetricsCalculator",
    "HeuristicsChecker",
    "AnomalyDetector",
    "ReportGenerator",
]
