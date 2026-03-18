"""
报纸大样PDF解析系统
Newspaper Layout PDF Parser

将原生报纸PDF解析为结构化JSON（Article Graph）
"""

__version__ = "0.4.0"
__author__ = "Claude Code"

from .schema import Block, BlockType, ZoneType, BBox, Article, PageResult
from .pdf_loader import PDFLoader
from .block_extractor import BlockExtractor
from .font_analyzer import FontAnalyzer
from .zone_segmenter import ZoneSegmenter
from .block_classifier import BlockClassifier
from .column_detector import ColumnDetector
from .article_builder import ArticleBuilder
from .reading_order import ReadingOrderBuilder
from .visualizer import Visualizer
from .utils import safe_execute, validate_pdf_path, create_output_directory
from .debug_report import DebugReporter

__all__ = [
    "Block",
    "BlockType",
    "ZoneType",
    "BBox",
    "Article",
    "PageResult",
    "PDFLoader",
    "BlockExtractor",
    "FontAnalyzer",
    "ZoneSegmenter",
    "BlockClassifier",
    "ColumnDetector",
    "ArticleBuilder",
    "ReadingOrderBuilder",
    "Visualizer",
    "safe_execute",
    "validate_pdf_path",
    "create_output_directory",
    "DebugReporter",
]
