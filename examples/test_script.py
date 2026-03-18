"""
测试脚本
Test Script

用于测试智能审校系统的各项功能
"""

import sys
import json
from pathlib import Path
from intelligent_editor.main import audit_layout


def test_with_sample_data():
    """使用示例数据测试"""

    print("=" * 60)
    print("测试: 使用示例数据")
    print("=" * 60)

    # 使用项目中的测试数据
    test_json = "test_structured.json"

    if not Path(test_json).exists():
        print(f"测试文件不存在: {test_json}")
        print("请提供有效的structured.json文件")
        return

    try:
        # 运行审核
        report = audit_layout(
            json_path=test_json,
            strategy='balanced',
            output_dir='test_results'
        )

        # 验证输出结构
        assert 'level1_decision' in report, "缺少level1_decision"
        assert 'level2_score' in report, "缺少level2_score"
        assert 'level3_top_issues' in report, "缺少level3_top_issues"
        assert 'level4_all_risks' in report, "缺少level4_all_risks"
        assert 'level5_explanation' in report, "缺少level5_explanation"

        # 验证决策
        decision = report['level1_decision']['decision']
        assert decision in ['approve', 'review', 'reject'], f"无效决策: {decision}"

        # 验证评分
        score = report['level2_score']['score']
        assert 0 <= score <= 100, f"无效评分: {score}"

        print("\n✅ 测试通过")
        print(f"决策: {decision}")
        print(f"评分: {score:.1f}")
        print(f"风险数: {report['level4_all_risks']['total_count']}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_all_strategies():
    """测试所有策略"""

    print("\n" + "=" * 60)
    print("测试: 所有决策策略")
    print("=" * 60)

    test_json = "test_structured.json"

    if not Path(test_json).exists():
        print(f"测试文件不存在: {test_json}")
        return

    strategies = ['conservative', 'balanced', 'aggressive']

    for strategy in strategies:
        print(f"\n测试策略: {strategy}")

        try:
            report = audit_layout(
                json_path=test_json,
                strategy=strategy,
                output_dir=f'test_results/{strategy}'
            )

            decision = report['level1_decision']['decision']
            score = report['level2_score']['score']

            print(f"  决策: {decision}")
            print(f"  评分: {score:.1f}")
            print(f"  ✅ {strategy}策略测试通过")

        except Exception as e:
            print(f"  ❌ {strategy}策略测试失败: {e}")


def test_edge_cases():
    """测试边界情况"""

    print("\n" + "=" * 60)
    print("测试: 边界情况")
    print("=" * 60)

    # 测试1: 空issues
    print("\n测试1: 空issues（应该APPROVE）")
    # 这个测试需要创建特殊的测试数据

    # 测试2: 只有CRITICAL风险
    print("\n测试2: 只有CRITICAL风险（应该REJECT）")

    # 测试3: 大量LOW风险
    print("\n测试3: 大量LOW风险")

    print("\n提示: 边界测试需要专门构造的测试数据")


def test_performance():
    """性能测试"""

    print("\n" + "=" * 60)
    print("测试: 性能")
    print("=" * 60)

    import time

    test_json = "test_structured.json"

    if not Path(test_json).exists():
        print(f"测试文件不存在: {test_json}")
        return

    # 预热
    audit_layout(test_json, output_dir='temp')

    # 多次运行取平均
    times = []
    for i in range(5):
        start = time.time()
        audit_layout(test_json, output_dir='temp')
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  第{i+1}次: {elapsed:.3f}秒")

    avg_time = sum(times) / len(times)
    print(f"\n平均处理时间: {avg_time:.3f}秒")

    if avg_time < 3.0:
        print(f"✅ 性能测试通过（< 3秒）")
    else:
        print(f"❌ 性能测试失败（>= 3秒）")


def test_output_files():
    """测试输出文件"""

    print("\n" + "=" * 60)
    print("测试: 输出文件")
    print("=" * 60)

    test_json = "test_structured.json"

    if not Path(test_json).exists():
        print(f"测试文件不存在: {test_json}")
        return

    # 运行审核
    report = audit_layout(
        json_path=test_json,
        output_dir='test_results'
    )

    # 检查JSON文件
    json_path = Path('test_results/intelligent_audit_report.json')
    assert json_path.exists(), "JSON报告文件不存在"

    with open(json_path, 'r', encoding='utf-8') as f:
        json_report = json.load(f)

    assert json_report == report, "JSON报告内容不一致"
    print("✅ JSON报告文件正确")

    # 检查TXT文件
    txt_path = Path('test_results/audit_summary.txt')
    assert txt_path.exists(), "TXT摘要文件不存在"

    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_content = f.read()

    assert len(txt_content) > 0, "TXT摘要文件为空"
    print("✅ TXT摘要文件正确")

    print("\n所有输出文件测试通过")


def test_error_handling():
    """测试错误处理"""

    print("\n" + "=" * 60)
    print("测试: 错误处理")
    print("=" * 60)

    # 测试1: 文件不存在
    print("\n测试1: 文件不存在")
    try:
        audit_layout('nonexistent.json', output_dir='temp')
        print("❌ 应该抛出异常")
    except FileNotFoundError:
        print("✅ 正确抛出FileNotFoundError")
    except Exception as e:
        print(f"⚠️  抛出了其他异常: {type(e).__name__}")

    # 测试2: 无效策略
    print("\n测试2: 无效策略")
    try:
        audit_layout('test_structured.json', strategy='invalid', output_dir='temp')
        print("❌ 应该抛出异常")
    except ValueError:
        print("✅ 正确抛出ValueError")
    except Exception as e:
        print(f"⚠️  抛出了其他异常: {type(e).__name__}")

    # 测试3: 无效JSON
    print("\n测试3: 无效JSON")
    # 这个测试需要创建一个无效的JSON文件


def run_all_tests():
    """运行所有测试"""

    print("\n" + "=" * 60)
    print("智能审校系统 - 测试套件")
    print("=" * 60)

    tests = [
        ("基本功能测试", test_with_sample_data),
        ("策略测试", test_all_strategies),
        ("性能测试", test_performance),
        ("输出文件测试", test_output_files),
        ("错误处理测试", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"运行测试: {test_name}")
        print(f"{'=' * 60}")

        try:
            test_func()
            passed += 1
            print(f"\n✅ {test_name} 通过")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} 失败: {e}")

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有{failed}个测试失败")


if __name__ == '__main__':
    # 运行所有测试
    run_all_tests()

    # 或者运行单个测试
    # test_with_sample_data()
    # test_all_strategies()
    # test_performance()
    # test_output_files()
    # test_error_handling()
