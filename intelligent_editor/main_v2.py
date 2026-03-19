"""
CLI entry point for the redesigned dual-channel intelligent editor report.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_editor.audit_runner import decision_to_exit_code, run_base_audit
from intelligent_editor.core.editorial_optimizer import EditorialOptimizer
from intelligent_editor.core.editorial_quality_engine import EditorialQualityEngine
from intelligent_editor.core.safety_evaluator import SafetyEvaluator
from intelligent_editor.models.editorial_quality import (
    DualChannelReport,
    ImpactLevel,
    PublicationDecision,
)
from intelligent_editor.models.executive_report import (
    EngineeringBaselineFinding,
    EngineeringBaselineReport,
    ExecutiveAuditReport,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("intelligent_editor")


def audit_layout_v2(
    json_path: str,
    strategy: str = "balanced",
    output_dir: str = "editor_results_v2",
) -> DualChannelReport:
    """Generate the compatibility dual-channel report and new executive outputs."""
    start_time = datetime.now()
    artifacts = run_base_audit(json_path, strategy)

    editorial_engine = EditorialQualityEngine(
        artifacts.configs.get("editorial_quality", {})
    )
    quality_improvement = editorial_engine.generate_quality_assessment(
        artifacts.data,
        artifacts.metrics,
        artifacts.risks,
    )

    blocking_issues = [item.summary for item in artifacts.top_issues]
    publication_decision = PublicationDecision(
        decision=artifacts.decision.type.value,
        risk_level=artifacts.decision.risk_level.name,
        confidence=artifacts.decision.confidence,
        blocking_issues=blocking_issues,
        reasoning=artifacts.decision.reasoning,
    )

    processing_time = (datetime.now() - start_time).total_seconds()
    metadata = {
        "processing_time": f"{processing_time:.2f}s",
        "timestamp": datetime.now().isoformat(),
        "strategy": strategy,
        "version": "v2.1",
    }
    report = DualChannelReport(
        publication_decision=publication_decision,
        quality_improvement=quality_improvement,
        metadata=metadata,
    )

    executive_report = _build_executive_report(artifacts, quality_improvement, metadata)
    _save_dual_channel_report(report, executive_report, artifacts.data, output_dir)
    logger.info("Dual-channel audit completed in %.2fs", processing_time)
    return report


def _build_executive_report(
    artifacts: Any,
    quality_improvement: Any,
    metadata: Dict[str, Any],
) -> ExecutiveAuditReport:
    safety_report = SafetyEvaluator(
        artifacts.configs.get("safety_evaluation", {})
    ).evaluate(
        artifacts.decision,
        artifacts.top_issues,
        artifacts.risks,
        artifacts.data,
    )
    optimization_report = EditorialOptimizer(
        artifacts.configs.get("optimization_generation", {})
    ).build_report(quality_improvement)
    engineering_baseline = _build_engineering_baseline(artifacts.top_issues)

    executive_summary = {
        "overall_recommendation": safety_report.recommendation,
        "risk_level": safety_report.risk_level,
        "headline": "总编辑主报告已切换为安全评估与优化决策双主线。",
        "safety_focus": safety_report.summary,
        "optimization_focus": optimization_report.summary,
        "manual_review_required": safety_report.requires_manual_review,
        "engineering_findings_hidden_in_appendix": True,
    }

    return ExecutiveAuditReport(
        executive_summary=executive_summary,
        safety_report=safety_report,
        optimization_report=optimization_report,
        engineering_baseline=engineering_baseline,
        metadata=metadata,
    )


def _build_engineering_baseline(top_issues: Iterable[Any]) -> EngineeringBaselineReport:
    findings: List[EngineeringBaselineFinding] = []
    for issue in list(top_issues)[:5]:
        findings.append(
            EngineeringBaselineFinding(
                severity=issue.risk.severity.name,
                summary=issue.summary,
                action=issue.action_needed,
                source="rule_baseline",
            )
        )

    status = "attention_needed" if findings else "clear"
    note = (
        "版面工程问题仅作为底线校验附录展示，不再直接占用总编辑主报告。"
        if findings
        else "未发现明显版面工程底线问题。"
    )
    return EngineeringBaselineReport(
        status=status,
        finding_count=len(findings),
        findings=findings,
        note=note,
    )


def _save_dual_channel_report(
    report: DualChannelReport,
    executive_report: ExecutiveAuditReport,
    structured_data: Dict[str, Any],
    output_dir: str,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    (output_path / "intelligent_audit_report_v2.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_path / "executive_audit_report.json").write_text(
        json.dumps(executive_report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _save_editor_friendly_report_v2(output_path / "editor_report_v2.txt", report)
    _save_improvement_report(
        output_path / "improvement_suggestions.md",
        report,
        structured_data,
    )
    _save_safety_report(output_path / "safety_report.md", executive_report)
    _save_optimization_report(output_path / "optimization_report.md", executive_report)


def _target_label(value: str) -> str:
    return {
        "headline": "标题",
        "lead": "导语",
        "packaging": "包装",
        "homogeneity": "同质化",
    }.get(value, value)


def _impact_label(value: str) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(value, value)


def _translate_text(text: str) -> str:
    if not text:
        return text

    translations = {
        "Core stories are workable, but packaging and page diversity still need attention.": "核心稿件基础可用，但包装完整度和版面多样性仍需加强。",
        "Page packaging is reasonably balanced": "版面包装整体较为均衡。",
        "Story presentation remains diverse": "稿件呈现方式保持一定多样性。",
        "Lead openings should front-load stronger facts": "导语开头应更早抛出核心事实。",
        "Page packaging and visual hierarchy need work": "版面包装和视觉层级仍需加强。",
        "News value is not front-loaded": "导语核心信息前置不足",
        "The lead does not foreground the result, change, or impact early enough.": "导语没有在开头及时交代结果、变化或影响。",
        "Front-load the most newsworthy outcome or change.": "把最关键的结果或变化提前到导语开头。",
        "Improves scanability and reader attention.": "能提升扫读效率和读者注意力。",
        "The headline exceeds the configured length budget.": "标题超出了当前设定的长度预算。",
        "Compress to about 12-20 characters.": "建议压缩到约 12 到 20 字。",
        "A tighter headline is easier to scan.": "标题更紧凑后更利于扫读。",
        "Page has no image support": "整版缺少图片或图示支撑",
        "A multi-story page without any image support can feel visually heavy.": "多稿件版面如果完全没有图片支撑，视觉上会显得偏重。",
        "No image blocks were attached to any article.": "当前没有任何稿件挂接图片块。",
        "Consider adding at least one supporting image or infographic.": "建议补入至少一张配图或一处图示信息。",
        "Improves visual rhythm and reduces text density.": "能改善版面节奏并降低文字压迫感。",
    }
    if text in translations:
        return translations[text]

    headline_match = re.match(r"Headline is too long \((\d+) chars\)(.*)", text)
    if headline_match:
        count = headline_match.group(1)
        suffix = headline_match.group(2)
        return f"标题长度偏长（{count}字）{suffix}"

    if text.startswith("News value is not front-loaded"):
        suffix = text[len("News value is not front-loaded") :]
        return f"导语核心信息前置不足{suffix}"

    if text.startswith("[front-load the most newsworthy result or change]"):
        return text.replace(
            "[front-load the most newsworthy result or change]",
            "[在导语开头先交代最重要的结果或变化]",
        )

    return text


def _translate_list(items: Iterable[str]) -> List[str]:
    return [_translate_text(item) for item in items]


def _save_editor_friendly_report_v2(
    file_path: Path,
    report: DualChannelReport,
) -> None:
    decision = report.publication_decision
    quality = report.quality_improvement
    assessment = quality.assessment

    lines = [
        "智能审校报告 v2.1",
        "",
        "发布决策",
        f"- 决策: {decision.decision.upper()}",
        f"- 风险等级: {decision.risk_level}",
        f"- 置信度: {decision.confidence:.1%}",
        f"- 判断依据: {decision.reasoning}",
        "",
    ]

    if decision.blocking_issues:
        lines.append("当前阻断项")
        for issue in decision.blocking_issues:
            lines.append(f"- {issue}")
        lines.append("")

    lines.extend(
        [
            "质量评估",
            f"- 一句话判断: {_translate_text(assessment.overall_editorial_assessment)}",
            f"- 综合得分: {assessment.overall_score:.0f}/100 ({assessment.overall_grade})",
            f"- 标题质量: {assessment.headline_quality_score:.0f}/100",
            f"- 导语质量: {assessment.lead_quality_score:.0f}/100",
            f"- 包装质量: {assessment.packaging_quality_score:.0f}/100",
            f"- 多样性: {assessment.diversity_score:.0f}/100",
            "",
        ]
    )

    if assessment.strengths:
        lines.append("当前优势")
        for item in _translate_list(assessment.strengths):
            lines.append(f"- {item}")
        lines.append("")

    if assessment.improvement_areas:
        lines.append("重点改进方向")
        for item in _translate_list(assessment.improvement_areas):
            lines.append(f"- {item}")
        lines.append("")

    if quality.top_improvement_points:
        lines.append("Top 3 优化建议")
        for index, suggestion in enumerate(quality.top_improvement_points, start=1):
            lines.append(
                f"{index}. [{_target_label(suggestion.target.value)}] {_translate_text(suggestion.issue)}"
            )
            lines.append(f"   建议: {_translate_text(suggestion.lightweight_suggestion)}")
            lines.append(
                f"   预期收益: {_translate_text(suggestion.expected_improvement)}"
            )
        lines.append("")

    lines.extend(
        [
            "元数据",
            f"- 处理时间: {report.metadata['processing_time']}",
            f"- 审校策略: {report.metadata['strategy']}",
            f"- 版本: {report.metadata['version']}",
            f"- 生成时间: {report.metadata['timestamp']}",
        ]
    )

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _save_improvement_report(
    file_path: Path,
    report: DualChannelReport,
    structured_data: Dict[str, Any],
) -> None:
    quality = report.quality_improvement
    assessment = quality.assessment

    lines = [
        "# 版面质量提升建议报告",
        "",
        f"**生成时间**: {report.metadata['timestamp']}",
        f"**综合质量**: {assessment.overall_score:.0f}/100",
        f"**建议数量**: {quality.total_suggestions}",
        "",
        "## 总体判断",
        "",
        f"**一句话判断**: {_translate_text(assessment.overall_editorial_assessment)}",
        "",
        f"- **标题质量**: {assessment.headline_quality_score:.0f}/100",
        f"- **导语质量**: {assessment.lead_quality_score:.0f}/100",
        f"- **包装质量**: {assessment.packaging_quality_score:.0f}/100",
        f"- **内容多样性**: {assessment.diversity_score:.0f}/100",
        "",
    ]

    if assessment.strengths:
        lines.append("## 当前优势")
        lines.append("")
        for item in _translate_list(assessment.strengths):
            lines.append(f"- {item}")
        lines.append("")

    if assessment.improvement_areas:
        lines.append("## 重点改进方向")
        lines.append("")
        for item in _translate_list(assessment.improvement_areas):
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Top 3 优化建议")
    lines.append("")
    for index, suggestion in enumerate(quality.top_improvement_points, start=1):
        lines.append(f"### {index}. {_translate_text(suggestion.issue)}")
        lines.append("")
        lines.append(f"- **目标类型**: {_target_label(suggestion.target.value)}")
        lines.append(f"- **影响级别**: {_impact_label(suggestion.impact_level.value)}")
        lines.append(f"- **位置**: `{suggestion.article_id}`")
        if suggestion.original_text:
            lines.append(f"- **原文片段**: `{suggestion.original_text}`")
        lines.append(f"- **原因**: {_translate_text(suggestion.reason)}")
        lines.append(f"- **建议**: {_translate_text(suggestion.lightweight_suggestion)}")
        lines.append(
            f"- **预期收益**: {_translate_text(suggestion.expected_improvement)}"
        )
        lines.append("")

    if quality.headline_suggestions:
        lines.append("## 标题详细建议")
        lines.append("")
        for suggestion in quality.headline_suggestions:
            lines.append(f"### {suggestion.article_id}")
            lines.append("")
            lines.append(f"- **标题**: {suggestion.headline_text}")
            lines.append(f"- **问题类型**: {suggestion.issue_type.value}")
            lines.append(
                f"- **问题说明**: {_translate_text(suggestion.issue_description)}"
            )
            lines.append(f"- **原因**: {_translate_text(suggestion.reason)}")
            lines.append(f"- **建议**: {_translate_text(suggestion.lightweight_suggestion)}")
            if suggestion.alternative_headlines:
                lines.append("- **可选标题**:")
                for alt in suggestion.alternative_headlines:
                    lines.append(f"  - {alt}")
            lines.append("")

    if quality.lead_suggestions:
        lines.append("## 导语详细建议")
        lines.append("")
        for suggestion in quality.lead_suggestions:
            lines.append(f"### {suggestion.article_id}")
            lines.append("")
            lines.append(f"- **问题类型**: {suggestion.issue_type.value}")
            lines.append(f"- **原文**: `{suggestion.lead_text[:200]}`")
            lines.append(f"- **原因**: {_translate_text(suggestion.reason)}")
            lines.append(f"- **建议**: {_translate_text(suggestion.lightweight_suggestion)}")
            if suggestion.revised_lead_example:
                lines.append(
                    f"- **改写示例**: `{_translate_text(suggestion.revised_lead_example)}`"
                )
            lines.append("")

    if quality.packaging_suggestions:
        lines.append("## 包装详细建议")
        lines.append("")
        for suggestion in quality.packaging_suggestions:
            lines.append(f"### {suggestion.article_id}")
            lines.append("")
            lines.append(f"- **问题类型**: {suggestion.issue_type.value}")
            lines.append(
                f"- **问题说明**: {_translate_text(suggestion.issue_description)}"
            )
            lines.append(f"- **现状**: {_translate_text(suggestion.current_state)}")
            lines.append(f"- **原因**: {_translate_text(suggestion.reason)}")
            lines.append(f"- **建议**: {_translate_text(suggestion.lightweight_suggestion)}")
            lines.append("")

    if quality.homogeneity_suggestions:
        lines.append("## 同质化详细建议")
        lines.append("")
        for suggestion in quality.homogeneity_suggestions:
            lines.append(f"### {', '.join(suggestion.article_ids)}")
            lines.append("")
            lines.append(f"- **问题类型**: {suggestion.issue_type}")
            lines.append(
                f"- **问题说明**: {_translate_text(suggestion.issue_description)}"
            )
            lines.append(
                f"- **相似性分析**: {_translate_text(suggestion.similarity_analysis)}"
            )
            lines.append(f"- **原因**: {_translate_text(suggestion.reason)}")
            lines.append(f"- **建议**: {_translate_text(suggestion.lightweight_suggestion)}")
            lines.append("")

    if structured_data.get("articles"):
        lines.append("## 数据概览")
        lines.append("")
        lines.append(f"- **文章数**: {len(structured_data['articles'])}")
        lines.append(f"- **版面块数**: {len(structured_data.get('blocks', []))}")
        lines.append("")

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _save_safety_report(file_path: Path, executive_report: ExecutiveAuditReport) -> None:
    safety = executive_report.safety_report
    lines = [
        "# 总编辑安全报告",
        "",
        f"**建议结论**: {safety.recommendation.upper()}",
        f"**风险等级**: {safety.risk_level}",
        f"**语义安全链已启用**: {'是' if safety.semantic_review_enabled else '否'}",
        f"**是否需要人工复核**: {'是' if safety.requires_manual_review else '否'}",
        "",
        "## 核心判断",
        "",
        safety.summary,
        "",
    ]

    if safety.findings:
        lines.append("## 重点安全事项")
        lines.append("")
        for index, finding in enumerate(safety.findings, start=1):
            lines.append(f"### {index}. {finding.title}")
            lines.append("")
            lines.append(f"- **级别**: {finding.level}")
            lines.append(f"- **说明**: {finding.detail}")
            lines.append(f"- **动作**: {finding.action}")
            lines.append(f"- **来源**: {finding.source}")
            lines.append(
                f"- **需人工复核**: {'是' if finding.requires_manual_review else '否'}"
            )
            lines.append("")

    if safety.note:
        lines.append("## 说明")
        lines.append("")
        lines.append(safety.note)
        lines.append("")

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _save_optimization_report(
    file_path: Path, executive_report: ExecutiveAuditReport
) -> None:
    optimization = executive_report.optimization_report
    engineering = executive_report.engineering_baseline
    lines = [
        "# 总编辑优化报告",
        "",
        optimization.summary,
        "",
    ]

    if optimization.tasks:
        lines.append("## Top 编辑任务")
        lines.append("")
        for index, task in enumerate(optimization.tasks, start=1):
            lines.append(f"### {index}. {task.title}")
            lines.append("")
            lines.append(f"- **优先级**: {task.priority}")
            lines.append(f"- **任务类型**: {task.task_type}")
            lines.append(f"- **为什么要改**: {task.why_it_matters}")
            if task.article_ids:
                lines.append(f"- **涉及稿件**: {', '.join(task.article_ids)}")
            lines.append(f"- **来源**: {task.source}")
            lines.append("")
            lines.append("可选方案")
            for option in task.options:
                lines.append(f"- **{option.label}**: {option.content}")
                lines.append(f"  适用: {option.fit_for}")
                lines.append(f"  理由: {option.rationale}")
            lines.append("")

    lines.extend(
        [
            "## 底线附录",
            "",
            engineering.note,
            "",
        ]
    )
    for finding in engineering.findings:
        lines.append(f"- [{finding.severity}] {finding.summary}")
        lines.append(f"  处理: {finding.action}")

    file_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        description="智能审校系统 v2.1 - 总编辑安全报告 + 优化报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m intelligent_editor.main_v2 page_1_structured.json
    python -m intelligent_editor.main_v2 page_1_structured.json --strategy conservative
    python -m intelligent_editor.main_v2 page_1_structured.json --output-dir results
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
        default="editor_results_v2",
        help="输出目录，默认 editor_results_v2",
    )
    args = parser.parse_args()

    try:
        report = audit_layout_v2(args.json_path, args.strategy, args.output_dir)
        decision = report.publication_decision
        quality = report.quality_improvement
        print()
        print("=" * 60)
        print("智能审校完成 v2.1")
        print("=" * 60)
        print(f"决策: {decision.decision.upper()}")
        print(f"风险等级: {decision.risk_level}")
        print(
            f"编辑质量: {quality.assessment.overall_score:.0f}/100 "
            f"({quality.assessment.overall_grade})"
        )
        print(f"优化建议: {quality.total_suggestions} 条")
        print("=" * 60)
        print(f"\n报告已保存到: {args.output_dir}")
        return decision_to_exit_code(decision.decision)
    except Exception as exc:
        logger.error("Audit failed: %s", exc)
        import traceback

        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
