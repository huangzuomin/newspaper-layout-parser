"""
Main entry point for the PDF parser CLI.
"""

import argparse
import json
import logging
import logging.config
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import yaml

from .article_builder import ArticleBuilder
from .block_classifier import BlockClassifier
from .block_extractor import BlockExtractor
from .column_detector import ColumnDetector
from .font_analyzer import FontAnalyzer
from .pdf_loader import PDFLoader
from .reading_order import ReadingOrderBuilder
from .schema import PageResult
from .visualizer import Visualizer
from .zone_segmenter import ZoneSegmenter


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure parser logging."""
    config_path = Path(__file__).parent / "config" / "logging.yaml"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as handle:
            log_config = yaml.safe_load(handle)

        log_config["loggers"]["parser"]["level"] = log_level
        log_config["handlers"]["console"]["level"] = log_level

        if log_file:
            log_config["handlers"]["file"]["filename"] = log_file

        logging.config.dictConfig(log_config)
        return

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_page_range(page_range: str, page_count: int) -> List[int]:
    """Parse a page range string into zero-based page indexes."""
    if not page_range or page_range.lower() == "all":
        return list(range(page_count))

    if "-" in page_range:
        start_text, end_text = page_range.split("-", 1)
        start = int(start_text)
        end = int(end_text)
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"Invalid page range: {page_range}")
        return list(range(start - 1, end))

    page_no = int(page_range)
    if page_no < 1 or page_no > page_count:
        raise ValueError(f"Invalid page number: {page_range}")
    return [page_no - 1]


def _prepare_output_dirs(output_path: Path) -> None:
    for name in ("json", "overlays", "snapshots", "logs"):
        (output_path / name).mkdir(parents=True, exist_ok=True)


def _parse_single_page(
    loader: PDFLoader,
    page_no: int,
    extractor: BlockExtractor,
) -> PageResult:
    logger = logging.getLogger("parser")

    page = loader.load_page(page_no)
    page_width, page_height = loader.get_page_dimensions(page_no)
    logger.info("Processing page %s (%sx%s)", page_no + 1, int(page_width), int(page_height))

    blocks = extractor.extract_blocks(page, page_no)
    blocks = extractor.filter_blocks(blocks, min_chars=3)

    font_analyzer = FontAnalyzer()
    font_profile = font_analyzer.analyze(blocks)

    zone_segmenter = ZoneSegmenter()
    blocks = zone_segmenter.segment(blocks, page_width, page_height)

    classifier = BlockClassifier()
    blocks = classifier.classify_candidates(blocks, font_profile)

    column_detector = ColumnDetector()
    blocks = column_detector.detect(blocks)

    blocks = classifier.finalize_classification(blocks)

    article_builder = ArticleBuilder()
    articles = article_builder.build(blocks)

    reading_order_builder = ReadingOrderBuilder()
    block_order, article_order = reading_order_builder.build(blocks, articles)

    return PageResult(
        page_no=page_no + 1,
        width=page_width,
        height=page_height,
        blocks=blocks,
        articles=articles,
        block_reading_order=block_order,
        article_reading_order=article_order,
        font_profile=font_profile,
    )


def parse_pdf(
    pdf_path: str,
    output_dir: str,
    log_level: str = "INFO",
    page_range: str = "all",
) -> dict:
    """Parse a PDF file into page-level structured results."""
    logger = logging.getLogger("parser")
    output_path = Path(output_dir)
    _prepare_output_dirs(output_path)

    logger.info("Processing PDF: %s", pdf_path)
    logger.info("Output directory: %s", output_dir)

    loader = PDFLoader(pdf_path)
    extractor = BlockExtractor()

    try:
        page_indexes = parse_page_range(page_range, loader.page_count)
        logger.info("Selected pages: %s", ", ".join(str(i + 1) for i in page_indexes))

        pages: List[PageResult] = []
        for page_index in page_indexes:
            result = _parse_single_page(loader, page_index, extractor)
            pages.append(result)
            _save_intermediate_results(result, output_path)

        aggregated = {
            "pages": [page.to_dict() for page in pages],
            "total_pages": loader.page_count,
            "processed_pages": len(pages),
            "pdf_path": pdf_path,
            "page_range": page_range,
        }

        parsed_result_path = output_path / "json" / "parsed_result.json"
        with open(parsed_result_path, "w", encoding="utf-8") as handle:
            json.dump(aggregated, handle, ensure_ascii=False, indent=2)
        logger.info("Saved aggregated result: %s", parsed_result_path)

        return aggregated
    finally:
        loader.close()


def _save_intermediate_results(result: PageResult, output_path: Path) -> None:
    """Persist per-page artifacts."""
    logger = logging.getLogger("parser")
    page_no = result.page_no

    raw_blocks_payload = {
        "page_no": result.page_no,
        "width": result.width,
        "height": result.height,
        "blocks": [block.to_dict() for block in result.blocks],
    }

    raw_blocks_path = output_path / "json" / f"page_{page_no}_raw_blocks.json"
    with open(raw_blocks_path, "w", encoding="utf-8") as handle:
        json.dump(raw_blocks_payload, handle, ensure_ascii=False, indent=2)
    logger.info("Saved raw blocks: %s", raw_blocks_path)

    structured_path = output_path / "json" / f"page_{page_no}_structured.json"
    with open(structured_path, "w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, ensure_ascii=False, indent=2)
    logger.info("Saved structured data: %s", structured_path)

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
    logger.info("Saved raw visualization: %s", raw_overlay_path)

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
    logger.info("Saved structure visualization: %s", structure_overlay_path)

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
        logger.info("Saved articles visualization: %s", articles_overlay_path)

    from .debug_report import DebugReporter

    debug_report_path = output_path / "logs" / f"page_{page_no}_debug_report.txt"
    reporter = DebugReporter(result.to_dict(), result.width, result.height)
    reporter.generate_report(str(debug_report_path))
    logger.info("Generated debug report: %s", debug_report_path)


def main() -> int:
    """CLI entry point."""
    cli = argparse.ArgumentParser(
        description="Newspaper Layout PDF Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cli.add_argument("pdf_path", help="Path to the PDF file")
    cli.add_argument("--output-dir", "-o", default="output", help="Output directory")
    cli.add_argument(
        "--log-level",
        "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )
    cli.add_argument(
        "--page-range",
        default="all",
        help='Pages to process, e.g. "all", "1", or "1-3"',
    )
    cli.add_argument("--version", "-v", action="version", version="%(prog)s 0.4.0")
    args = cli.parse_args()

    output_path = Path(args.output_dir)
    (output_path / "logs").mkdir(parents=True, exist_ok=True)

    log_file = output_path / "logs" / "parser.log"
    setup_logging(args.log_level, str(log_file))

    logger = logging.getLogger("parser")
    logger.info("=" * 60)
    logger.info("Newspaper Layout PDF Parser v0.4.0")
    logger.info("=" * 60)

    try:
        result = parse_pdf(
            args.pdf_path,
            args.output_dir,
            args.log_level,
            page_range=args.page_range,
        )

        total_blocks = sum(len(page["blocks"]) for page in result["pages"])
        total_articles = sum(len(page["articles"]) for page in result["pages"])
        logger.info("[OK] Successfully parsed %s pages", result["processed_pages"])
        logger.info("[OK] Blocks: %s", total_blocks)
        logger.info("[OK] Articles: %s", total_articles)
        logger.info("[OK] Output saved to: %s", args.output_dir)
        return 0
    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        return 1
    except ValueError as exc:
        logger.error("Invalid input: %s", exc)
        return 1
    except Exception as exc:
        logger.exception("Error parsing PDF: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
