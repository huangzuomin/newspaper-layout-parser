"""
工具函数模块
Utility functions for error handling and validation
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional
import traceback


logger = logging.getLogger("parser")


class PDFParseError(Exception):
    """PDF解析错误基类"""
    pass


class PDFLoadError(PDFParseError):
    """PDF加载错误"""
    pass


class BlockExtractionError(PDFParseError):
    """Block提取错误"""
    pass


class AnalysisError(PDFParseError):
    """分析错误（字体/zone/column/classification）"""
    pass


def safe_execute(
    func_name: str,
    func,
    *args,
    default_value: Any = None,
    raise_on_error: bool = False,
    **kwargs
) -> Any:
    """
    安全执行函数，带错误处理

    Args:
        func_name: 函数名称
        func: 函数对象
        default_value: 出错时的默认返回值
        raise_on_error: 是否重新抛出异常
        *args, **kwargs: 函数参数

    Returns:
        函数结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func_name}: {e}")
        logger.debug(traceback.format_exc())

        if raise_on_error:
            raise
        return default_value


def validate_pdf_path(pdf_path: str) -> Path:
    """
    验证PDF文件路径

    Args:
        pdf_path: PDF文件路径

    Returns:
        Path对象

    Raises:
        PDFLoadError: 文件不存在或不是PDF
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PDFLoadError(f"PDF file not found: {pdf_path}")

    if not path.is_file():
        raise PDFLoadError(f"Path is not a file: {pdf_path}")

    # 检查扩展名
    if path.suffix.lower() not in ['.pdf']:
        logger.warning(f"File does not have .pdf extension: {pdf_path}")

    return path


def create_output_directory(output_dir: str) -> Path:
    """
    创建输出目录结构

    Args:
        output_dir: 输出目录路径

    Returns:
        Path对象
    """
    output_path = Path(output_dir)

    # 创建所有必需的子目录
    (output_path / "json").mkdir(parents=True, exist_ok=True)
    (output_path / "overlays").mkdir(parents=True, exist_ok=True)
    (output_path / "snapshots").mkdir(parents=True, exist_ok=True)
    (output_path / "logs").mkdir(parents=True, exist_ok=True)

    logger.debug(f"Output directory created: {output_dir}")
    return output_path


def log_page_summary(page_no: int, blocks_count: int, articles_count: int):
    """
    记录页面处理摘要

    Args:
        page_no: 页码
        blocks_count: blocks数量
        articles_count: articles数量
    """
    logger.info(
        f"Page {page_no} summary: "
        f"{blocks_count} blocks, {articles_count} articles"
    )


def format_processing_time(elapsed_seconds: float) -> str:
    """
    格式化处理时间

    Args:
        elapsed_seconds: 经过的秒数

    Returns:
        格式化的时间字符串
    """
    if elapsed_seconds < 1:
        return f"{elapsed_seconds * 1000:.0f}ms"
    elif elapsed_seconds < 60:
        return f"{elapsed_seconds:.1f}s"
    else:
        minutes = int(elapsed_seconds // 60)
        seconds = elapsed_seconds % 60
        return f"{minutes}m {seconds:.0f}s"
