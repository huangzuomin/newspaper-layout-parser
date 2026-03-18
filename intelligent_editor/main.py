"""
智能审校系统CLI入口
Intelligent Editor System - Main Entry Point
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_auditor import MetricsCalculator, HeuristicsChecker, AnomalyDetector
from intelligent_editor.core.risk_engine import RiskEngine
from intelligent_editor.core.decision_engine import DecisionEngine
from intelligent_editor.core.scoring_engine import ScoringEngine
from intelligent_editor.core.explanation_engine import ExplanationEngine
from intelligent_editor.core.top_issues_extractor import TopIssuesExtractor
from intelligent_editor.core.optimization_engine import OptimizationEngine
from intelligent_editor.utils.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intelligent_editor")


def audit_layout(
    json_path: str,
    strategy: str = 'balanced',
    output_dir: str = 'editor_results'
) -> Dict[str, Any]:
    """
    智能审校主函数

    Args:
        json_path: parser输出的structured.json路径
        strategy: 决策策略（conservative/balanced/aggressive）
        output_dir: 输出目录

    Returns:
        5层输出报告字典

    Raises:
        FileNotFoundError: 如果JSON文件不存在
        ValueError: 如果策略名称无效
        json.JSONDecodeError: 如果JSON格式无效
    """
    start_time = datetime.now()
    logger.info(f"Starting intelligent audit for {json_path}")

    # 1. 加载解析结果
    logger.info("Loading structured.json...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {json_path}")
        raise FileNotFoundError(f"无法找到文件: {json_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        raise ValueError(f"JSON格式无效: {e}")

    # 2. 调用parser_auditor获取质量评估
    logger.info("Running parser_auditor...")
    metrics_calculator = MetricsCalculator(data)
    metrics = metrics_calculator.calculate_all_metrics()

    heuristics_checker = HeuristicsChecker(data)
    issues = heuristics_checker.check_all()

    anomaly_detector = AnomalyDetector(data)
    anomalies = anomaly_detector.detect_all()

    logger.info(f"Found {len(issues)} issues and {sum(len(v) for v in anomalies.values())} anomalies")

    # 3. 加载配置并验证策略
    logger.info("Loading intelligent_editor configs...")
    configs = ConfigLoader.load_all_configs()

    # 验证策略名称
    valid_strategies = configs['decision'].get('strategies', {}).keys()
    if strategy not in valid_strategies:
        raise ValueError(
            f"无效的策略名称: '{strategy}'. "
            f"有效策略: {', '.join(valid_strategies)}"
        )

    # 4. 初始化智能审校系统
    risk_engine = RiskEngine(configs['risk'])
    decision_engine = DecisionEngine(configs['decision'])
    scoring_engine = ScoringEngine(configs['scoring'])
    explanation_engine = ExplanationEngine(configs.get('explanation', {}))
    top_issues_extractor = TopIssuesExtractor(configs.get('top_issues', {}))
    optimization_engine = OptimizationEngine(configs.get('optimization', {}))

    # 5. 执行审校流程
    logger.info("Identifying risks...")
    risks = risk_engine.identify_risks(issues, anomalies, metrics)

    logger.info("Calculating score...")
    score = scoring_engine.calculate_score(risks, metrics)

    logger.info("Making decision...")
    decision = decision_engine.make_decision(risks, metrics, strategy)

    logger.info("Extracting top issues...")
    top_issues = top_issues_extractor.extract_top_issues(risks, decision)

    # 6. 生成解释
    logger.info("Generating explanations...")
    explanation = explanation_engine.generate_explanation(
        decision, score, top_issues, risks
    )

    # 6.5 生成优化建议
    logger.info("Generating optimization suggestions...")
    optimization_report = optimization_engine.generate_suggestions(
        data, metrics, risks
    )

    # 7. 生成输出报告
    logger.info("Generating report...")
    report = _generate_report(
        decision,
        score,
        risks,
        top_issues,
        explanation,
        optimization_report,
        start_time,
        strategy
    )

    # 7. 保存报告
    _save_report(report, output_dir)

    processing_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Audit completed in {processing_time:.2f}s")

    return report


def _generate_report(
    decision,
    score,
    risks: list,
    top_issues: list,
    explanation,
    optimization_report,
    start_time: datetime,
    strategy: str
) -> Dict[str, Any]:
    """
    生成6层输出报告（新增优化建议层）

    Args:
        decision: 决策对象
        score: 评分对象
        risks: 风险列表
        top_issues: Top问题列表
        explanation: 解释对象
        optimization_report: 优化建议报告
        start_time: 开始时间
        strategy: 决策策略名称

    Returns:
        6层输出报告字典
    """
    processing_time = (datetime.now() - start_time).total_seconds()

    # 统计各级风险数量
    risk_statistics = {
        'critical': sum(1 for r in risks if r.severity.name == 'CRITICAL'),
        'high': sum(1 for r in risks if r.severity.name == 'HIGH'),
        'medium': sum(1 for r in risks if r.severity.name == 'MEDIUM'),
        'low': sum(1 for r in risks if r.severity.name == 'LOW'),
    }

    report = {
        # Level 1: 决策层（总编辑只看这个）
        'level1_decision': {
            'decision': decision.type.value,
            'risk_level': decision.risk_level.name,
            'confidence': f"{decision.confidence:.1%}",
            'reasoning': decision.reasoning,
        },

        # Level 2: 评分层
        'level2_score': score.to_dict(),

        # Level 3: Top问题层
        'level3_top_issues': [
            issue.to_dict() for issue in top_issues
        ],

        # Level 4: 全部风险（默认隐藏）
        'level4_all_risks': {
            'total_count': len(risks),
            'risks': [risk.to_dict() for risk in risks]
        },

        # Level 5: 解释层（Phase 3新增）
        'level5_explanation': explanation.to_dict(),

        # Level 6: 优化建议层（新增）
        'level6_optimization': optimization_report.to_dict(),

        # 元数据
        'metadata': {
            'processing_time': f"{processing_time:.2f}s",
            'parser_confidence': 'high',  # Phase 1使用固定值
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy,  # 使用实际传入的策略
        }
    }

    # 将risk_statistics添加到level2_score中
    report['level2_score']['risk_statistics'] = risk_statistics

    return report


def _save_report(report: Dict[str, Any], output_dir: str):
    """
    保存报告

    Args:
        report: 报告字典
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存完整JSON报告
    report_file = output_path / "intelligent_audit_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved JSON report: {report_file}")

    # 保存人类可读摘要
    summary_file = output_path / "audit_summary.txt"
    _save_summary(summary_file, report)

    # 保存总编辑友好报告
    editor_report_file = output_path / "editor_report.txt"
    _save_editor_friendly_report(editor_report_file, report)

    logger.info(f"Saved summary: {summary_file}")
    logger.info(f"Saved editor report: {editor_report_file}")


def _save_summary(file_path: Path, report: Dict[str, Any]):
    """
    保存人类可读摘要

    Args:
        file_path: 文件路径
        report: 报告字典
    """
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("智能审校报告")
    lines.append("Intelligent Editor Audit Report")
    lines.append("=" * 60)
    lines.append("")

    # Level 1: 决策
    decision = report['level1_decision']
    lines.append("【决策】")
    lines.append(f"决策结果: {decision['decision'].upper()}")
    lines.append(f"风险等级: {decision['risk_level']}")
    lines.append(f"置信度: {decision['confidence']}")
    lines.append(f"决策依据: {decision['reasoning']}")
    lines.append("")

    # Level 2: 评分
    score_info = report['level2_score']
    lines.append("【评分】")
    lines.append(f"总分: {score_info['score']}/{100}")
    lines.append(f"等级: {score_info['grade']}")
    lines.append(f"基础分: {score_info['base_score']}")
    lines.append(f"风险扣分: -{score_info['risk_penalty']}")
    lines.append(f"加分: +{score_info['bonus']}")
    lines.append("")

    # Level 2: 风险统计
    risk_stats = score_info['risk_statistics']
    lines.append("【风险统计】")
    lines.append(f"CRITICAL: {risk_stats['critical']}")
    lines.append(f"HIGH: {risk_stats['high']}")
    lines.append(f"MEDIUM: {risk_stats['medium']}")
    lines.append(f"LOW: {risk_stats['low']}")
    lines.append("")

    # Level 3: Top问题
    top_issues = report['level3_top_issues']
    lines.append("【Top 问题】")
    if top_issues:
        for issue in top_issues:
            lines.append(f"{issue['rank']}. [{issue['severity']}] {issue['summary']}")
            lines.append(f"   建议: {issue['action_needed']}")
    else:
        lines.append("未发现问题")
    lines.append("")

    # 元数据
    metadata = report['metadata']
    lines.append("=" * 60)
    lines.append(f"处理时间: {metadata['processing_time']}")
    lines.append(f"报告时间: {metadata['timestamp']}")

    # 写入文件
    file_path.write_text("\n".join(lines), encoding='utf-8')


def _save_editor_friendly_report(file_path: Path, report: Dict[str, Any]):
    """
    保存总编辑友好报告

    特点:
    - 3秒阅读模式
    - 重点突出
    - 使用emoji增强可读性
    - 明确的行动建议

    Args:
        file_path: 文件路径
        report: 报告字典
    """
    lines = []

    # ═══════════════════════════════════════════════════════════
    # 报告标题
    # ═══════════════════════════════════════════════════════════
    lines.append("╔" + "═" * 58 + "╗")
    lines.append("║" + " " * 15 + "智能审校报告" + " " * 15 + "║")
    lines.append("║" + " " * 10 + "Intelligent Editor Audit Report" + " " * 10 + "║")
    lines.append("╚" + "═" * 58 + "╝")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 核心决策（3秒模式）
    # ═══════════════════════════════════════════════════════════
    decision = report['level1_decision']
    decision_type = decision['decision'].upper()

    # 根据决策类型选择emoji和颜色建议
    if decision_type == 'APPROVE':
        emoji = "✅"
        action = "可以付印"
        color_hint = ""
    elif decision_type == 'REVIEW':
        emoji = "⚠️"
        action = "建议重点审查"
        color_hint = ""
    else:  # REJECT
        emoji = "❌"
        action = "不能付印，必须修改"
        color_hint = ""

    lines.append("┏" + "━" * 58 + "┓")
    lines.append("┃" + " " * 20 + "【审校结论】" + " " * 20 + "┃")
    lines.append("┗" + "━" * 58 + "┛")
    lines.append("")
    lines.append(f"  {emoji}  决策: {decision_type}")
    lines.append(f"  📊  风险等级: {decision['risk_level']}")
    lines.append(f"  🎯  置信度: {decision['confidence']}")
    lines.append(f"  💡  建议: {action}")
    lines.append("")

    # 决策依据
    if decision.get('reasoning'):
        lines.append(f"  📝  依据: {decision['reasoning']}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 质量评分
    # ═══════════════════════════════════════════════════════════
    score_info = report['level2_score']
    score = score_info['score']
    grade = score_info['grade']

    # 根据等级选择emoji
    grade_emoji = {
        'A': '🌟',
        'B': '👍',
        'C': '😐',
        'D': '😟',
        'F': '❌'
    }.get(grade, '📊')

    lines.append("┏" + "━" * 58 + "┓")
    lines.append("┃" + " " * 20 + "【质量评分】" + " " * 20 + "┃")
    lines.append("┗" + "━" * 58 + "┛")
    lines.append("")
    lines.append(f"  {grade_emoji}  总分: {score:.1f}/100  ({grade}级)")
    lines.append("")

    # 评分细项（折叠显示）
    lines.append("  📊  评分组成:")
    lines.append(f"     ├─ 基础分: {score_info['base_score']}")
    lines.append(f"     ├─ 风险扣分: -{score_info['risk_penalty']}")
    lines.append(f"     └─ 加分: +{score_info['bonus']}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 风险统计（突出显示）
    # ═══════════════════════════════════════════════════════════
    risk_stats = score_info['risk_statistics']

    lines.append("┏" + "━" * 58 + "┓")
    lines.append("┃" + " " * 20 + "【风险统计】" + " " * 20 + "┃")
    lines.append("┗" + "━" * 58 + "┛")
    lines.append("")

    # 风险统计可视化
    critical = risk_stats['critical']
    high = risk_stats['high']
    medium = risk_stats['medium']
    low = risk_stats['low']

    # 只有当有风险时才显示
    if critical > 0 or high > 0 or medium > 0 or low > 0:
        if critical > 0:
            lines.append(f"  🔴  重大风险 (CRITICAL): {critical}")
        if high > 0:
            lines.append(f"  🟠  高风险 (HIGH): {high}")
        if medium > 0:
            lines.append(f"  🟡  中等风险 (MEDIUM): {medium}")
        if low > 0:
            lines.append(f"  🟢  轻微风险 (LOW): {low}")
        lines.append("")
    else:
        lines.append("  ✨  未发现任何风险")
        lines.append("")

    # ═══════════════════════════════════════════════════════════
    # Top问题（关键问题）
    # ═══════════════════════════════════════════════════════════
    top_issues = report['level3_top_issues']

    if top_issues:
        lines.append("┏" + "━" * 58 + "┓")
        lines.append("┃" + " " * 18 + "【需要关注的问题】" + " " * 18 + "┃")
        lines.append("┗" + "━" * 58 + "┛")
        lines.append("")

        for issue in top_issues:
            rank = issue['rank']
            severity = issue['severity']

            # 根据严重程度选择emoji
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(severity, '⚪')

            lines.append(f"  {severity_emoji}  问题 {rank}: {issue['summary']}")
            lines.append(f"     💡  建议: {issue['action_needed']}")
            lines.append("")
    else:
        # 没有Top问题的情况
        if critical == 0 and high == 0 and medium == 0:
            lines.append("┏" + "━" * 58 + "┓")
            lines.append("┃" + " " * 16 + "【✨ 版面质量优秀 ✨】" + " " * 17 + "┃")
            lines.append("┗" + "━" * 58 + "┛")
            lines.append("")
            lines.append("  🎉  恭喜！未发现需要重点关注的问题")
            lines.append("  📝  版面质量符合付印标准")
            lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 行动建议
    # ═══════════════════════════════════════════════════════════
    lines.append("┏" + "━" * 58 + "┓")
    lines.append("┃" + " " * 18 + "【行动建议】" + " " * 20 + "┃")
    lines.append("┗" + "━" * 58 + "┛")
    lines.append("")

    if decision_type == 'APPROVE':
        lines.append("  ✅  可以直接付印")
        lines.append("  📋  建议: 快速浏览版面，确认无误后签字付印")
    elif decision_type == 'REVIEW':
        lines.append("  ⚠️  建议重点审查上述问题")
        lines.append("  📋  建议: 逐一检查Top问题，确认是否需要修改")
    else:  # REJECT
        lines.append("  ❌  必须修改后才能付印")
        lines.append("  📋  建议: 优先处理重大风险，修改后重新审校")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 元数据
    # ═══════════════════════════════════════════════════════════
    metadata = report['metadata']

    lines.append("────────────────────────────────────────────────────────")
    lines.append(f"  ⏱️  处理时间: {metadata['processing_time']}")
    lines.append(f"  📅  审校时间: {metadata['timestamp'][:19].replace('T', ' ')}")
    lines.append(f"  🔧  审校策略: {metadata['strategy']}")
    lines.append("")

    # ═══════════════════════════════════════════════════════════
    # 页脚
    # ═══════════════════════════════════════════════════════════
    lines.append("╔" + "═" * 58 + "╗")
    lines.append("║" + " " * 12 + "智能审校系统 v1.0" + " " * 12 + "║")
    lines.append("║" + " " * 8 + "Intelligent Editor System" + " " * 9 + "║")
    lines.append("╚" + "═" * 58 + "╝")

    # 写入文件
    file_path.write_text("\n".join(lines), encoding='utf-8')


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="智能审校系统 - 总编辑版面决策支持系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python -m intelligent_editor.main page_1_structured.json

    # 指定决策策略
    python -m intelligent_editor.main page_1_structured.json --strategy conservative

    # 只显示决策摘要
    python -m intelligent_editor.main page_1_structured.json --summary-only

    # 指定输出目录
    python -m intelligent_editor.main page_1_structured.json --output-dir results
        """
    )

    parser.add_argument(
        'json_path',
        help='structured.json文件路径（必需）'
    )

    parser.add_argument(
        '--strategy',
        '-s',
        choices=['conservative', 'balanced', 'aggressive'],
        default='balanced',
        help='决策策略（默认：balanced）'
    )

    parser.add_argument(
        '--output-dir',
        '-o',
        default='editor_results',
        help='输出目录（默认：editor_results）'
    )

    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='只显示决策摘要（Level 1 + Level 3）'
    )

    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='安静模式，只输出决策结果'
    )

    args = parser.parse_args()

    try:
        # 执行审校
        report = audit_layout(
            args.json_path,
            args.strategy,
            args.output_dir
        )

        # 输出结果
        if args.quiet:
            # 安静模式：只输出决策
            decision = report['level1_decision']
            print(f"{decision['decision']}:{decision['risk_level']}:{decision['confidence']}")
        elif args.summary_only:
            # 摘要模式：Level 1 + Level 3
            decision = report['level1_decision']
            top_issues = report['level3_top_issues']

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
            if top_issues:
                for issue in top_issues:
                    print(f"  {issue['rank']}. [{issue['severity']}] {issue['summary']}")
                    print(f"     建议: {issue['action_needed']}")
            else:
                print("  未发现问题")
            print("=" * 60)
        else:
            # 完整输出
            print()
            print("=" * 60)
            print("智能审校完成")
            print("=" * 60)
            decision = report['level1_decision']
            score_info = report['level2_score']
            print(f"决策: {decision['decision'].upper()}")
            print(f"风险等级: {decision['risk_level']}")
            print(f"置信度: {decision['confidence']}")
            print(f"评分: {score_info['score']}/{100} ({score_info['grade']})")
            risk_stats = score_info['risk_statistics']
            print(f"风险: C={risk_stats['critical']}, H={risk_stats['high']}, M={risk_stats['medium']}, L={risk_stats['low']}")
            print("=" * 60)
            print(f"\n报告已保存到: {args.output_dir}")

        # 返回状态码
        decision = report['level1_decision']['decision']
        if decision == 'approve':
            return 0
        elif decision == 'review':
            return 1
        else:  # reject
            return 2

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
