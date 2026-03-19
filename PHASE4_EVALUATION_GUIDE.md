# Phase 4 评估指南

这份指南用于校准新版总编辑安全报告与优化报告，不再只检查“是否能产出文件”，而是检查“产出是否符合人工预期”。

## 当前评估范围

1. 安全报告评估
   - 是否保留正确的付印建议
   - 是否正确标注人工复核
   - 是否至少覆盖关键安全提示

2. 优化报告评估
   - 是否产出足够的总编辑任务
   - 是否覆盖标题、导语、包装三类核心任务
   - 每类任务是否至少提供最小可用方案数

## 样例文件

- [safety_eval_cases.json](K:\Work\大样审校\tests\fixtures\safety_eval_cases.json)
- [optimization_eval_cases.json](K:\Work\大样审校\tests\fixtures\optimization_eval_cases.json)

## 运行方式

```powershell
py -3 -m intelligent_editor.evaluate_phase4
```

默认会读取仓库里的评估样例，执行 `main_v2` 生成新版总编辑报告，并输出：

- `phase4_evaluation_report.json`

## 输出摘要

结果会给出 3 个通过率：

- `safety_pass_rate`
- `optimization_pass_rate`
- `overall_pass_rate`

## 下一步如何使用

1. 打开真实模型配置
2. 先跑一次当前评测，记录基线
3. 调整 prompt / schema / guardrail
4. 再次跑评测，比较通过率变化
5. 对低通过样例补充人工点评，继续扩充对照集
