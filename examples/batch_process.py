"""
批量处理示例
Batch Processing Example

批量处理多个PDF文件，适用于生产环境
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加parser模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.main import parse_pdf


def batch_process(
    pdf_dir: str,
    output_base: str = "output",
    file_pattern: str = "*.pdf",
):
    """
    批量处理PDF文件

    Args:
        pdf_dir: PDF文件目录
        output_base: 输出基础目录
        file_pattern: 文件匹配模式（默认：*.pdf）
    """
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    pdf_path = Path(pdf_dir)

    if not pdf_path.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        return

    # 查找所有PDF文件
    pdf_files = list(pdf_path.glob(file_pattern))

    if not pdf_files:
        logger.warning(f"No PDF files found in {pdf_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files to process")

    # 创建输出基础目录
    output_base_path = Path(output_base)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_output_dir = output_base_path / f"batch_{timestamp}"

    # 批量处理
    results = {
        "total": len(pdf_files),
        "successful": 0,
        "failed": 0,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "errors": [],
    }

    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")

        # 每个PDF有独立的输出目录
        output_dir = batch_output_dir / pdf_file.stem

        try:
            # 解析PDF
            parse_pdf(str(pdf_file), str(output_dir), "INFO")
            results["successful"] += 1
            logger.info(f"  ✓ Success: {pdf_file.name}")

        except Exception as e:
            results["failed"] += 1
            error_msg = f"{pdf_file.name}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"  ✗ Failed: {error_msg}")

    # 更新结束时间
    results["end_time"] = datetime.now().isoformat()

    # 保存批量处理结果
    results_file = batch_output_dir / "batch_results.json"
    import json
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n" + "=" * 60)
    logger.info("Batch processing completed")
    logger.info(f"Total: {results['total']}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Results saved to: {results_file}")
    logger.info("=" * 60)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="批量处理报纸PDF文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 处理单个目录下的所有PDF
    python batch_process.py "newspapers/" --output-dir output

    # 只处理特定模式的PDF
    python batch_process.py "data/" --pattern "2026-*.pdf" --output-dir output
        """
    )

    parser.add_argument(
        "pdf_dir",
        help="PDF文件目录",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="输出基础目录（默认：output）",
    )

    parser.add_argument(
        "--pattern",
        "-p",
        default="*.pdf",
        help="文件匹配模式（默认：*.pdf）",
    )

    args = parser.parse_args()

    batch_process(
        args.pdf_dir,
        args.output_dir,
        args.pattern,
    )


if __name__ == "__main__":
    main()
