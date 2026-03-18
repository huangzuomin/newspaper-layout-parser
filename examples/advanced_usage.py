"""
高级使用示例
Advanced Usage Example

演示高级功能：批量处理、自定义配置、结果分析
"""

from pathlib import Path
from intelligent_editor.main import audit_layout
from intelligent_editor.utils import ConfigLoader
import json


def example_batch_process():
    """批量处理多个版面"""

    print("=" * 60)
    print("批量处理示例")
    print("=" * 60)

    # 假设有一个目录包含多个structured.json
    json_dir = Path("path/to/structured_jsons")

    # 统计结果
    results = {
        'approve': 0,
        'review': 0,
        'reject': 0,
        'total': 0
    }

    # 遍历所有JSON文件
    for json_file in json_dir.glob("*.json"):
        print(f"\n处理: {json_file.name}")

        try:
            # 为每个文件创建独立的输出目录
            output_dir = f"batch_results/{json_file.stem}"

            # 审核版面
            report = audit_layout(
                json_path=str(json_file),
                strategy='balanced',
                output_dir=output_dir
            )

            # 统计决策
            decision = report['level1_decision']['decision']
            results[decision] += 1
            results['total'] += 1

            print(f"  决策: {decision}")
            print(f"  评分: {report['level2_score']['score']:.1f}")

        except Exception as e:
            print(f"  错误: {e}")

    # 输出统计
    print("\n" + "=" * 60)
    print("批量处理统计")
    print("=" * 60)
    print(f"总计: {results['total']}个版面")
    print(f"APPROVE: {results['approve']}个")
    print(f"REVIEW: {results['review']}个")
    print(f"REJECT: {results['reject']}个")


def example_custom_config():
    """使用自定义配置"""

    print("\n" + "=" * 60)
    print("自定义配置示例")
    print("=" * 60)

    # 1. 加载默认配置
    risk_config = ConfigLoader.load_config('risk_rules')

    # 2. 修改配置（示例：提高风险阈值）
    risk_config['severity_rules']['high']['threshold'] = 5  # 从3改为5

    # 3. 保存自定义配置
    custom_config_path = "intelligent_editor/config/risk_rules_custom.yaml"
    ConfigLoader.save_config(custom_config_path, risk_config)

    print(f"自定义配置已保存到: {custom_config_path}")

    # 注意：当前版本需要修改代码才能使用自定义配置
    # 未来版本可以添加 --config 参数


def example_analyze_results():
    """分析审核结果"""

    print("\n" + "=" * 60)
    print("结果分析示例")
    print("=" * 60)

    # 读取已生成的报告
    report_path = "editor_results/intelligent_audit_report.json"

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # 1. 决策分析
    decision = report['level1_decision']
    print(f"\n决策分析:")
    print(f"  类型: {decision['decision']}")
    print(f"  风险等级: {decision['risk_level']}")
    print(f"  置信度: {decision['confidence']}")

    # 2. 评分分析
    score = report['level2_score']
    print(f"\n评分分析:")
    print(f"  总分: {score['score']:.1f}")
    print(f"  等级: {score['grade']}")
    print(f"  基础分: {score['base_score']}")
    print(f"  扣分: {score['risk_penalty']}")
    print(f"  加分: {score['bonus']}")

    # 3. 风险统计
    risk_stats = score['risk_statistics']
    print(f"\n风险统计:")
    print(f"  CRITICAL: {risk_stats['critical']}")
    print(f"  HIGH: {risk_stats['high']}")
    print(f"  MEDIUM: {risk_stats['medium']}")
    print(f"  LOW: {risk_stats['low']}")
    print(f"  总计: {sum(risk_stats.values())}")

    # 4. Top问题分析
    top_issues = report['level3_top_issues']
    print(f"\nTop {len(top_issues)}问题:")
    for issue in top_issues:
        print(f"  {issue['rank']}. [{issue['severity']}] {issue['summary']}")
        print(f"     影响: {issue.get('impact', '')}")
        print(f"     建议: {issue['action_needed']}")

    # 5. 所有风险分析
    all_risks = report['level4_all_risks']['risks']

    # 按类型统计
    risk_types = {}
    for risk in all_risks:
        risk_type = risk['type']
        risk_types[risk_type] = risk_types.get(risk_type, 0) + 1

    print(f"\n风险类型分布:")
    for risk_type, count in sorted(risk_types.items(), key=lambda x: -x[1]):
        print(f"  {risk_type}: {count}")

    # 按严重程度统计
    severity_count = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for risk in all_risks:
        severity = risk['severity']
        severity_count[severity] += 1

    print(f"\n严重程度分布:")
    for severity, count in severity_count.items():
        print(f"  {severity}: {count}")


def example_export_to_csv():
    """导出结果到CSV"""

    print("\n" + "=" * 60)
    print("导出CSV示例")
    print("=" * 60)

    import csv

    # 批量处理多个版面并导出结果
    json_dir = Path("path/to/structured_jsons")
    csv_path = "audit_results.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # 写入表头
        writer.writerow([
            '文件名',
            '决策',
            '风险等级',
            '置信度',
            '总分',
            '等级',
            'CRITICAL',
            'HIGH',
            'MEDIUM',
            'LOW',
            '总风险数'
        ])

        # 处理每个JSON文件
        for json_file in json_dir.glob("*.json"):
            try:
                report = audit_layout(
                    json_path=str(json_file),
                    strategy='balanced',
                    output_dir=f'temp_results/{json_file.stem}'
                )

                # 提取数据
                decision = report['level1_decision']
                score = report['level2_score']
                risk_stats = score['risk_statistics']

                # 写入CSV
                writer.writerow([
                    json_file.name,
                    decision['decision'],
                    decision['risk_level'],
                    decision['confidence'],
                    f"{score['score']:.1f}",
                    score['grade'],
                    risk_stats['critical'],
                    risk_stats['high'],
                    risk_stats['medium'],
                    risk_stats['low'],
                    report['level4_all_risks']['total_count']
                ])

            except Exception as e:
                print(f"处理 {json_file.name} 时出错: {e}")

    print(f"结果已导出到: {csv_path}")


def example_compare_strategies():
    """比较不同策略的结果"""

    print("\n" + "=" * 60)
    print("策略比较示例")
    print("=" * 60)

    json_path = "path/to/page_1_structured.json"

    strategies = ['conservative', 'balanced', 'aggressive']
    results = {}

    for strategy in strategies:
        report = audit_layout(
            json_path=json_path,
            strategy=strategy,
            output_dir=f'compare_results/{strategy}'
        )

        results[strategy] = {
            'decision': report['level1_decision']['decision'],
            'risk_level': report['level1_decision']['risk_level'],
            'score': report['level2_score']['score'],
            'grade': report['level2_score']['grade']
        }

    # 比较结果
    print(f"\n{'策略':<15} {'决策':<10} {'风险等级':<10} {'评分':<10} {'等级':<5}")
    print("-" * 60)

    for strategy, result in results.items():
        print(
            f"{strategy:<15} "
            f"{result['decision']:<10} "
            f"{result['risk_level']:<10} "
            f"{result['score']:<10.1f} "
            f"{result['grade']:<5}"
        )


def example_filter_risks():
    """筛选特定类型的风险"""

    print("\n" + "=" * 60)
    print("风险筛选示例")
    print("=" * 60)

    # 读取报告
    report_path = "editor_results/intelligent_audit_report.json"

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    all_risks = report['level4_all_risks']['risks']

    # 1. 筛选CRITICAL风险
    critical_risks = [r for r in all_risks if r['severity'] == 'CRITICAL']
    print(f"\nCRITICAL风险 ({len(critical_risks)}个):")
    for risk in critical_risks:
        print(f"  - {risk['description']}")

    # 2. 筛选文章相关风险
    article_risks = [r for r in all_risks if 'article' in r['type']]
    print(f"\n文章相关风险 ({len(article_risks)}个):")
    for risk in article_risks[:5]:  # 只显示前5个
        print(f"  - {risk['type']}: {risk['description']}")

    # 3. 筛选版面相关风险
    layout_risks = [r for r in all_risks if 'layout' in r['type'] or 'block' in r['type']]
    print(f"\n版面相关风险 ({len(layout_risks)}个):")
    for risk in layout_risks[:5]:
        print(f"  - {risk['type']}: {risk['description']}")


if __name__ == '__main__':
    # 运行示例（根据需要取消注释）

    # example_batch_process()
    # example_custom_config()
    example_analyze_results()
    # example_export_to_csv()
    # example_compare_strategies()
    # example_filter_risks()
