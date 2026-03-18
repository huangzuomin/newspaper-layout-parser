"""
Parser Auditor CLI
命令行工具 - 用于评估PDF解析结果的质量

用法:
    python -m parser_auditor.main structured.json
    python -m parser_auditor.main structured.json --output-dir audit_results
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# 添加parser_auditor模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_auditor import MetricsCalculator, HeuristicsChecker, AnomalyDetector, ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parser_auditor")


def audit_json(
    json_path: str,
    output_dir: str = "audit_results"
) -> dict:
    """
    对解析结果JSON进行审计

    Args:
        json_path: structured.json文件路径
        output_dir: 输出目录

    Returns:
        审计报告字典
    """
    logger.info(f"Parsing JSON file: {json_path}")

    # 读取JSON文件
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        raise

    logger.info(f"Loaded data with {len(data.get('blocks', []))} blocks, {len(data.get('articles', []))} articles")

    # 1. 计算指标
    logger.info("Calculating metrics...")
    metrics_calculator = MetricsCalculator(data)
    metrics = metrics_calculator.calculate_all_metrics()

    # 2. 启发式检查
    logger.info("Running heuristic checks...")
    heuristics_checker = HeuristicsChecker(data)
    issues = heuristics_checker.check_all()

    # 3. 异常检测
    logger.info("Detecting anomalies...")
    anomaly_detector = AnomalyDetector(data)
    anomalies = anomaly_detector.detect_all()

    # 4. 生成报告
    logger.info("Generating report...")
    report_generator = ReportGenerator(metrics, issues, anomalies)
    report = report_generator.generate_report()

    # 5. 保存结果
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存完整报告JSON
    report_file = output_path / "audit_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved audit report: {report_file}")

    # 保存人类可读报告
    readable_report_file = output_path / "audit_report.txt"
    _save_readable_report(readable_report_file, report, metrics, issues, anomalies)

    logger.info(f"Saved readable report: {readable_report_file}")

    # 保存异常详情
    anomalies_file = output_path / "anomalies.json"
    with open(anomalies_file, 'w', encoding='utf-8') as f:
        json.dump(anomalies, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved anomalies details: {anomalies_file}")

    return report


def _save_readable_report(
    file_path: Path,
    report: dict,
    metrics: dict,
    issues: list,
    anomalies: dict
):
    """保存人类可读的报告"""
    lines = []
    lines.append("=" * 80)
    lines.append("PDF解析结果质量评估报告")
    lines.append("Parser Auditor Report")
    lines.append("=" * 80)
    lines.append("")

    # 总体评估
    lines.append("【总体评估】")
    lines.append("-" * 80)
    lines.append(f"总分: {report['score']}/100")
    lines.append(f"置信度: {report['confidence'].upper()}")
    lines.append("")

    # 分数细项
    lines.append("【分数细项】")
    lines.append("-" * 80)
    breakdown = report.get('score_breakdown', {})
    lines.append(f"Block质量: {breakdown.get('block_quality', 0)}/25")
    lines.append(f"Article质量: {breakdown.get('article_quality', 0)}/35")
    lines.append(f"Column质量: {breakdown.get('column_quality', 0)}/20")
    lines.append(f"Zone质量: {breakdown.get('zone_quality', 0)}/10")
    lines.append(f"全局质量: {breakdown.get('global_quality', 0)}/10")
    lines.append("")

    # 问题汇总
    lines.append("【问题汇总】")
    lines.append("-" * 80)
    issue_summary = report.get('issues', {})
    lines.append(f"总Issues数: {issue_summary.get('total_issues', 0)}")
    lines.append(f"总异常数: {issue_summary.get('total_anomalies', 0)}")
    lines.append("")

    by_severity = issue_summary.get('by_severity', {})
    for severity in ['critical', 'high', 'medium', 'low']:
        items = by_severity.get(severity, [])
        if items:
            lines.append(f"{severity.upper()} ({len(items)}):")
            for item in items:
                lines.append(f"  - [{item.get('type', 'unknown')}] {item.get('reason', '')}")
            lines.append("")

    # 关键指标
    lines.append("【关键指标】")
    lines.append("-" * 80)

    block_metrics = metrics.get('blocks', {})
    lines.append(f"总Blocks: {block_metrics.get('total', 0)}")
    lines.append(f"类型分布: {block_metrics.get('type_distribution', {})}")
    lines.append("")

    article_metrics = metrics.get('articles', {})
    lines.append(f"总Articles: {article_metrics.get('total', 0)}")
    lines.append(f"Headline覆盖率: {article_metrics.get('headline_coverage', 0):.1%}")
    lines.append(f"低置信度文章: {article_metrics.get('low_confidence_count', 0)}")
    lines.append("")

    column_metrics = metrics.get('columns', {})
    lines.append(f"总栏数: {column_metrics.get('total', 0)}")
    lines.append("")

    # 改进建议
    lines.append("【改进建议】")
    lines.append("-" * 80)
    for i, suggestion in enumerate(report.get('suggestions', []), 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")

    # 时间戳
    lines.append("=" * 80)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 写入文件
    file_path.write_text("\n".join(lines), encoding='utf-8')


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="PDF解析结果质量评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 评估解析结果
    python -m parser_auditor.main output/json/page_1_structured.json

    # 指定输出目录
    python -m parser_auditor.main page_1_structured.json --output-dir audit_results

    # 只显示分数
    python -m parser_auditor.main page_1_structured.json --score-only
        """
    )

    parser.add_argument(
        'json_path',
        help='structured.json文件路径（必需）'
    )

    parser.add_argument(
        '--output-dir',
        '-o',
        default='audit_results',
        help='输出目录（默认：audit_results）'
    )

    parser.add_argument(
        '--score-only',
        action='store_true',
        help='只显示分数，不保存详细报告'
    )

    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='安静模式，只输出分数'
    )

    args = parser.parse_args()

    try:
        # 执行审计
        report = audit_json(args.json_path, args.output_dir)

        # 输出结果
        if args.quiet:
            # 安静模式：只输出分数
            print(f"{report['score']}:{report['confidence']}")
        elif args.score_only:
            # 只显示分数和置信度
            print(f"Score: {report['score']}/100")
            print(f"Confidence: {report['confidence'].upper()}")
            print(f"Issues: {report['issues']['total_issues']}")
            print(f"Anomalies: {report['issues']['total_anomalies']}")
        else:
            # 完整输出
            print()
            print("=" * 60)
            print("PDF解析结果质量评估")
            print("=" * 60)
            print(f"Score: {report['score']}/100")
            print(f"Confidence: {report['confidence'].upper()}")
            print(f"Issues: {report['issues']['total_issues']}")
            print(f"Anomalies: {report['issues']['total_anomalies']}")
            print("=" * 60)

        # 返回状态码
        score = report['score']
        if score >= 80:
            return 0
        elif score >= 60:
            return 1
        else:
            return 2

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
