"""
主入口模块
Main entry point for the PDF parser CLI

Usage:
    python -m parser.main "path/to/pdf.pdf" --output-dir output --log-level INFO
"""

import argparse
import json
import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

import yaml

from .pdf_loader import PDFLoader
from .block_extractor import BlockExtractor
from .visualizer import Visualizer
from .font_analyzer import FontAnalyzer
from .zone_segmenter import ZoneSegmenter
from .block_classifier import BlockClassifier
from .column_detector import ColumnDetector
from .article_builder import ArticleBuilder
from .reading_order import ReadingOrderBuilder
from .schema import PageResult

# 加载日志配置
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    设置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径（可选）
    """
    # 读取日志配置
    config_path = Path(__file__).parent / "config" / "logging.yaml"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            log_config = yaml.safe_load(f)

        # 更新日志级别
        log_config["loggers"]["parser"]["level"] = log_level
        log_config["handlers"]["console"]["level"] = log_level

        # 更新日志文件路径
        if log_file:
            log_config["handlers"]["file"]["filename"] = log_file

        logging.config.dictConfig(log_config)
    else:
        # 降级到基本配置
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def parse_pdf(
    pdf_path: str,
    output_dir: str,
    log_level: str = "INFO",
) -> PageResult:
    """
    解析PDF文件

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        log_level: 日志级别

    Returns:
        PageResult对象
    """
    logger = logging.getLogger("parser")

    # 创建输出目录
    output_path = Path(output_dir)
    (output_path / "json").mkdir(parents=True, exist_ok=True)
    (output_path / "overlays").mkdir(parents=True, exist_ok=True)
    (output_path / "snapshots").mkdir(parents=True, exist_ok=True)
    (output_path / "logs").mkdir(parents=True, exist_ok=True)

    logger.info(f"Processing PDF: {pdf_path}")
    logger.info(f"Output directory: {output_dir}")

    # 初始化组件
    loader = PDFLoader(pdf_path)
    extractor = BlockExtractor()
    visualizer = Visualizer()

    # 获取页数
    page_count = loader.page_count
    logger.info(f"PDF has {page_count} pages")

    # 目前只处理第一页（里程碑1）
    page_no = 0
    logger.info(f"Processing page {page_no + 1}/{page_count}")

    # 加载页面
    page = loader.load_page(page_no)
    page_width, page_height = loader.get_page_dimensions(page_no)
    logger.info(f"Page size: {page_width:.0f} x {page_height:.0f} points")

    # 提取blocks
    blocks = extractor.extract_blocks(page, page_no)

    # 过滤小blocks
    blocks = extractor.filter_blocks(blocks, min_chars=3)
    logger.info(f"Filtered to {len(blocks)} blocks")

    # ===== 里程碑2：结构分析 =====

    # 1. 字体分析
    font_analyzer = FontAnalyzer()
    font_profile = font_analyzer.analyze(blocks)
    logger.info("Font analysis completed")

    # 2. 区域分区
    zone_segmenter = ZoneSegmenter()
    blocks = zone_segmenter.segment(blocks, page_width, page_height)
    logger.info("Zone segmentation completed")

    # 3. Block候选分类（第一阶段）
    classifier = BlockClassifier()
    blocks = classifier.classify_candidates(blocks, font_profile)
    logger.info("Candidate classification completed")

    # 4. 分栏检测
    column_detector = ColumnDetector()
    blocks = column_detector.detect(blocks)
    logger.info("Column detection completed")

    # ===== 里程碑3：文章分析 =====

    # 5. Block最终分类（第二阶段）
    blocks = classifier.finalize_classification(blocks)
    logger.info("Final classification completed")

    # 6. 文章聚类
    article_builder = ArticleBuilder()
    articles = article_builder.build(blocks)
    logger.info(f"Article clustering completed: {len(articles)} articles")

    # 7. 阅读顺序构建
    reading_order_builder = ReadingOrderBuilder()
    block_order, article_order = reading_order_builder.build(blocks, articles)
    logger.info("Reading order completed")

    # 创建PageResult
    result = PageResult(
        page_no=page_no + 1,
        width=page_width,
        height=page_height,
        blocks=blocks,
        articles=articles,
        block_reading_order=block_order,
        article_reading_order=article_order,
        font_profile=font_profile,  # 保存字体配置
    )

    # 关闭PDF
    loader.close()

    # 保存中间产物
    _save_intermediate_results(result, output_path, page_no + 1)

    logger.info("PDF parsing completed")
    return result


def _save_intermediate_results(result: PageResult, output_path: Path, page_no: int):
    """
    保存中间产物

    Args:
        result: PageResult对象
        output_path: 输出目录Path对象
        page_no: 页码
    """
    logger = logging.getLogger("parser")

    # 1. 保存raw_blocks.json
    raw_blocks_path = output_path / "json" / f"page_{page_no}_raw_blocks.json"
    with open(raw_blocks_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved raw blocks: {raw_blocks_path}")

    # 2. 生成page_N_raw.png可视化
    visualizer = Visualizer()
    raw_overlay_path = output_path / "overlays" / f"page_{page_no}_raw.png"
    visualizer.visualize_raw_blocks(
        result.blocks,
        result.width,
        result.height,
        str(raw_overlay_path),
        show_block_ids=True,
        show_font_sizes=True,
    )
    logger.info(f"Saved raw visualization: {raw_overlay_path}")

    # 3. 生成structured.json
    structured_path = output_path / "json" / f"page_{page_no}_structured.json"
    with open(structured_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Saved structured data: {structured_path}")

    # 4. 生成page_N_structure.png可视化（里程碑2）
    structure_overlay_path = output_path / "overlays" / f"page_{page_no}_structure.png"
    visualizer.visualize_structure(
        result.blocks,
        result.width,
        result.height,
        str(structure_overlay_path),
        show_zones=True,
        show_columns=True,
        show_block_types=True,
    )
    logger.info(f"Saved structure visualization: {structure_overlay_path}")

    # 5. 生成page_N_articles.png可视化（里程碑3）
    if result.articles:
        articles_overlay_path = output_path / "overlays" / f"page_{page_no}_articles.png"
        visualizer.visualize_articles(
            result.blocks,
            result.articles,
            result.width,
            result.height,
            str(articles_overlay_path),
            show_article_bounds=True,
            show_article_connections=True,
            show_reading_order=True,
            block_order=result.block_reading_order,
            article_order=result.article_reading_order,
        )
        logger.info(f"Saved articles visualization: {articles_overlay_path}")

    # 4. 生成调试报告
    from .debug_report import DebugReporter
    debug_report_path = output_path / "logs" / f"page_{page_no}_debug_report.txt"
    reporter = DebugReporter(result.to_dict(), result.width, result.height)
    reporter.generate_report(str(debug_report_path))
    logger.info(f"Generated debug report: {debug_report_path}")


def main():
    """CLI主函数"""
    parser = argparse.ArgumentParser(
        description="报纸大样PDF解析系统 - Newspaper Layout PDF Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m parser.main "版面解析/B2026-03-18要闻一版01.pdf" --output-dir output
    python -m parser.main "test.pdf" --output-dir output --log-level DEBUG
        """,
    )

    parser.add_argument(
        "pdf_path",
        help="PDF文件路径",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="输出目录（默认：output）",
    )

    parser.add_argument(
        "--log-level",
        "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（默认：INFO）",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.4.0",
    )

    args = parser.parse_args()

    # 创建输出目录（在设置日志之前）
    output_path = Path(args.output_dir)
    (output_path / "logs").mkdir(parents=True, exist_ok=True)

    # 设置日志
    log_file = output_path / "logs" / "parser.log"
    setup_logging(args.log_level, str(log_file))

    logger = logging.getLogger("parser")
    logger.info("=" * 60)
    logger.info("Newspaper Layout PDF Parser v0.4.0 (Milestone 4)")
    logger.info("=" * 60)

    try:
        # 解析PDF
        result = parse_pdf(args.pdf_path, args.output_dir, args.log_level)

        # 输出统计信息
        logger.info(f"[OK] Successfully parsed {len(result.blocks)} blocks")
        logger.info(f"[OK] Articles: {len(result.articles)}")
        logger.info(f"[OK] Font analysis: method={result.font_profile.get('method', 'unknown')}")
        logger.info(f"[OK] Output saved to: {args.output_dir}")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Error parsing PDF: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
