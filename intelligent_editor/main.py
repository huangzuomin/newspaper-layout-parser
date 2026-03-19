"""
CLI entry point for the publication-focused intelligent editor report.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_editor.audit_runner import decision_to_exit_code, run_base_audit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("intelligent_editor")


def audit_layout(
    json_path: str,
    strategy: str = "balanced",
    output_dir: str = "editor_results",
) -> Dict[str, Any]:
    """Generate the publication-oriented report."""
    start_time = datetime.now()
    artifacts = run_base_audit(json_path, strategy)
    report = _generate_report(artifacts, start_time, strategy)
    _save_report(report, output_dir)
    logger.info(
        "Publication audit completed in %.2fs",
        (datetime.now() - start_time).total_seconds(),
    )
    return report


def _generate_report(artifacts, start_time: datetime, strategy: str) -> Dict[str, Any]:
    processing_time = (datetime.now() - start_time).total_seconds()
    risks = artifacts.risks

    risk_statistics = {
        "critical": sum(1 for risk in risks if risk.severity.name == "CRITICAL"),
        "high": sum(1 for risk in risks if risk.severity.name == "HIGH"),
        "medium": sum(1 for risk in risks if risk.severity.name == "MEDIUM"),
        "low": sum(1 for risk in risks if risk.severity.name == "LOW"),
    }

    report = {
        "level1_decision": {
            "decision": artifacts.decision.type.value,
            "risk_level": artifacts.decision.risk_level.name,
            "confidence": f"{artifacts.decision.confidence:.1%}",
            "reasoning": artifacts.decision.reasoning,
        },
        "level2_score": artifacts.score.to_dict(),
        "level3_top_issues": [issue.to_dict() for issue in artifacts.top_issues],
        "level4_all_risks": {
            "total_count": len(risks),
            "risks": [risk.to_dict() for risk in risks],
        },
        "level5_explanation": artifacts.explanation.to_dict(),
        "level6_optimization": artifacts.optimization_report.to_dict(),
        "metadata": {
            "processing_time": f"{processing_time:.2f}s",
            "parser_confidence": "high",
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy,
        },
    }
    report["level2_score"]["risk_statistics"] = risk_statistics
    return report


def _save_report(report: Dict[str, Any], output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_file = output_path / "intelligent_audit_report.json"
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _save_summary(output_path / "audit_summary.txt", report)
    _save_editor_friendly_report(output_path / "editor_report.txt", report)

    logger.info("Saved JSON report: %s", report_file)


def _save_summary(file_path: Path, report: Dict[str, Any]) -> None:
    decision = report["level1_decision"]
    score_info = report["level2_score"]
    risk_stats = score_info["risk_statistics"]
    top_issues = report["level3_top_issues"]
    metadata = report["metadata"]

    lines = [
        "智能审校报告",
        "Intelligent Editor Audit Report",
        "",
        "[决策]",
        f"决策结果: {decision['decision'].upper()}",
        f"风险等级: {decision['risk_level']}",
        f"置信度: {decision['confidence']}",
        f"决策依据: {decision['reasoning']}",
        "",
        "[评分]",
        f"总分: {score_info['score']}/100",
        f"等级: {score_info['grade']}",
        f"基础分: {score_info['base_score']}",
        f"风险扣分: -{score_info['risk_penalty']}",
        f"加分: +{score_info['bonus']}",
        "",
        "[风险统计]",
        f"CRITICAL: {risk_stats['critical']}",
        f"HIGH: {risk_stats['high']}",
        f"MEDIUM: {risk_stats['medium']}",
        f"LOW: {risk_stats['low']}",
        "",
        "[Top 问题]",
    ]

    if top_issues:
        for issue in top_issues:
            lines.append(f"{issue['rank']}. [{issue['severity']}] {issue['summary']}")
            lines.append(f"   建议: {issue['action_needed']}")
    else:
        lines.append("未发现需要优先处理的问题")

    lines.extend(
        [
            "",
            f"处理时间: {metadata['processing_time']}",
            f"报告时间: {metadata['timestamp']}",
        ]
    )

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _save_editor_friendly_report(file_path: Path, report: Dict[str, Any]) -> None:
    decision = report["level1_decision"]
    score_info = report["level2_score"]
    top_issues = report["level3_top_issues"]
    metadata = report["metadata"]

    lines = [
        "智能审校报告",
        "",
        "一眼结论",
        f"- 决策: {decision['decision'].upper()}",
        f"- 风险等级: {decision['risk_level']}",
        f"- 置信度: {decision['confidence']}",
        f"- 综合得分: {score_info['score']}/100 ({score_info['grade']})",
        "",
        "判断依据",
        decision["reasoning"],
        "",
        "优先处理的问题",
    ]

    if top_issues:
        for issue in top_issues:
            lines.append(
                f"- [{issue['severity']}] {issue['summary']} | 建议: {issue['action_needed']}"
            )
    else:
        lines.append("- 当前没有需要优先处理的阻断项")

    lines.extend(
        [
            "",
            "元数据",
            f"- 处理时间: {metadata['processing_time']}",
            f"- 审校策略: {metadata['strategy']}",
            f"- 生成时间: {metadata['timestamp']}",
        ]
    )

    file_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        description="智能审校系统 - 付印决策报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m intelligent_editor.main page_1_structured.json
    python -m intelligent_editor.main page_1_structured.json --strategy conservative
    python -m intelligent_editor.main page_1_structured.json --summary-only
    python -m intelligent_editor.main page_1_structured.json --output-dir results
        """,
    )
    parser.add_argument("json_path", help="structured.json 文件路径")
    parser.add_argument(
        "--strategy",
        "-s",
        choices=["conservative", "balanced", "aggressive"],
        default="balanced",
        help="决策策略，默认 balanced",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="editor_results",
        help="输出目录，默认 editor_results",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="仅输出决策摘要",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="安静模式，只输出决策结果",
    )
    args = parser.parse_args()

    try:
        report = audit_layout(args.json_path, args.strategy, args.output_dir)
        decision = report["level1_decision"]

        if args.quiet:
            print(
                f"{decision['decision']}:{decision['risk_level']}:{decision['confidence']}"
            )
        elif args.summary_only:
            print()
            print("=" * 60)
            print("决策结果")
            print("=" * 60)
            print(f"决策: {decision['decision'].upper()}")
            print(f"风险等级: {decision['risk_level']}")
            print(f"置信度: {decision['confidence']}")
            print(f"依据: {decision['reasoning']}")
            print()
            print("Top 问题:")
            for issue in report["level3_top_issues"] or []:
                print(f"  {issue['rank']}. [{issue['severity']}] {issue['summary']}")
                print(f"     建议: {issue['action_needed']}")
            if not report["level3_top_issues"]:
                print("  未发现需要优先处理的问题")
            print("=" * 60)
        else:
            score_info = report["level2_score"]
            risk_stats = score_info["risk_statistics"]
            print()
            print("=" * 60)
            print("智能审校完成")
            print("=" * 60)
            print(f"决策: {decision['decision'].upper()}")
            print(f"风险等级: {decision['risk_level']}")
            print(f"置信度: {decision['confidence']}")
            print(f"评分: {score_info['score']}/100 ({score_info['grade']})")
            print(
                "风险: "
                f"C={risk_stats['critical']}, "
                f"H={risk_stats['high']}, "
                f"M={risk_stats['medium']}, "
                f"L={risk_stats['low']}"
            )
            print("=" * 60)
            print(f"\n报告已保存到: {args.output_dir}")

        return decision_to_exit_code(decision["decision"])
    except Exception as exc:
        logger.error("Audit failed: %s", exc)
        import traceback

        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
