# 智能审校系统 - 用户使用指南

**Intelligent Editor System - User Guide**

---

## 📖 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [详细使用说明](#详细使用说明)
4. [配置文件说明](#配置文件说明)
5. [常见问题解答](#常见问题解答)
6. [最佳实践](#最佳实践)
7. [故障排除](#故障排除)

---

## 系统概述

### 什么是智能审校系统？

智能审校系统是一个**总编辑版面决策支持系统**，帮助总编辑在3秒内完成以下判断：

- ✅ 是否可以付印
- ✅ 是否存在重大风险
- ✅ 是否需要重点修改

### 系统特点

1. **输出结论优先** - 首先告诉你决策结果
2. **风险优先** - 关注影响而非错误数量
3. **信息压缩** - 只显示Top 3最重要的问题
4. **所有判断可解释** - 每个决策都有清晰依据

### 与传统校对工具的区别

| 传统校对工具 | 智能审校系统 |
|-------------|---------------|
| 找错（列出所有错误） | 做决策（approve/reject/reject） |
| 关注细节（标点、错别字） | 关注风险（重大风险、高风险） |
| 输出长列表 | 输出Top 3问题 |
| 需要人工逐一检查 | 3秒内完成判断 |

---

## 快速开始

### 第一步：准备输入文件

确保你有一个parser输出的`structured.json`文件：

```json
{
  "page_no": 1,
  "width": 965.34,
  "height": 1471.59,
  "blocks": [...],
  "articles": [...],
  "block_reading_order": [...],
  "article_reading_order": [...],
  "font_profile": {...}
}
```

### 第二步：运行智能审校

```bash
# 基本用法
python -m intelligent_editor.main page_1_structured.json

# 只看决策（3秒模式）
python -m intelligent_editor.main page_1_structured.json --summary-only
```

### 第三步：查看结果

**控制台输出**：
```
============================================================
智能审校完成
============================================================
决策: APPROVE
风险等级: LOW
评分: 92.0/100 (A)
置信度: 95.0%
============================================================
```

**输出文件**：
- `editor_results/intelligent_audit_report.json` - 完整5层JSON报告
- `editor_results/audit_summary.txt` - 人类可读摘要

---

## 详细使用说明

### 1. 基本用法

#### 审核单个版面

```bash
python -m intelligent_editor.main path/to/structured.json
```

**输出**：
- 完整的5层输出报告
- 保存到`editor_results/`目录

#### 只查看决策摘要

```bash
python -m intelligent_editor.main path/to/structured.json --summary-only
```

**输出**：
```
============================================================
决策结果
============================================================
决策: APPROVE
风险等级: LOW
置信度: 95.0%
依据: 整体质量良好，可以付印

Top 问题:
  未发现问题
============================================================
```

#### 安静模式（脚本集成）

```bash
python -m intelligent_editor.main path/to/structured.json --quiet
```

**输出**：
```
approve:low:95%
```

返回码：
- `0` - approve
- `1` - review
- `2` - reject

### 2. 选择决策策略

系统提供三种决策策略，适应不同的审校场景：

#### Conservative（保守策略）

**适用场景**：重大事件、重要版面

```bash
python -m intelligent_editor.main path/to/structured.json --strategy conservative
```

**特点**：
- 宁可误拒，不可漏报
- 对风险零容忍
- 适用于：党报头版、重大新闻版

#### Balanced（平衡策略）✨推荐

**适用场景**：日常审版工作

```bash
python -m intelligent_editor.main path/to/structured.json --strategy balanced
```

**特点**：
- 在准确率和召回率之间平衡
- 默认策略
- 适用于：日常新闻版面

#### Aggressive（激进策略）

**适用场景**：时间紧迫、快速审核

```bash
python -m intelligent_editor.main path/to/structured.json --strategy aggressive
```

**特点**：
- 宁可漏报，不可误拒
- 对风险容忍度高
- 适用于：紧急版面、快速审稿

### 3. 指定输出目录

```bash
python -m intelligent_editor.main path/to/structured.json --output-dir custom_results
```

输出文件将保存到`custom_results/`目录。

---

## 配置文件说明

### 1. risk_rules.yaml（风险规则配置）

**位置**：`intelligent_editor/config/risk_rules.yaml`

**作用**：定义如何将issues/anomalies映射到risks

**主要配置项**：

```yaml
# Issue到Risk的映射
issue_mappings:
  missing_headline: critical_article_risk
  too_many_columns: high_layout_risk
  empty_block: low_block_risk

# 风险严重等级定义
severity_rules:
  critical:
    threshold: 4
    description: "会导致付印事故"
    requires_rejection: true
```

**调整建议**：
- 如果某个风险类型被误判，可以调整映射关系
- 如果风险等级不符合实际，可以调整threshold

### 2. decision_strategy.yaml（决策策略配置）

**位置**：`intelligent_editor/config/decision_strategy.yaml`

**作用**：定义三种决策策略的阈值

**主要配置项**：

```yaml
strategies:
  balanced:
    thresholds:
      approve:
        max_critical: 0
        max_high: 1
        max_medium: 3
```

**调整建议**：
- 根据报社标准调整阈值
- 如果approve过于宽松，降低max_high和max_medium
- 如果reject过于频繁，提高阈值

### 3. scoring_weights.yaml（评分权重配置）

**位置**：`intelligent_editor/config/scoring_weights.yaml`

**作用**：定义风险扣分和质量等级

**主要配置项**：

```yaml
# 风险扣分权重
risk_weights:
  CRITICAL: 30
  HIGH: 15
  MEDIUM: 5
  LOW: 1

# 质量等级划分
grade_thresholds:
  A: 90
  B: 80
  C: 70
  D: 60
```

**调整建议**：
- 根据实际需求调整扣分权重
- 根据报社标准调整等级阈值

### 4. explanation_templates.yaml（解释模板配置）

**位置**：`intelligent_editor/config/explanation_templates.yaml`

**作用**：定义各种解释的自然语言模板

**主要配置项**：

```yaml
decision_templates:
  approve:
    short: "版面质量良好，可以付印"
    detailed: "版面质量评估为{grade}级..."
```

**调整建议**：
- 根据报社术语调整解释文本
- 使解释更符合业务场景

---

## 常见问题解答

### Q1: 为什么决策是REJECT但我觉得可以付印？

**A**: 可能的原因：

1. **风险阈值设置过于严格** - 调整`decision_strategy.yaml`中的阈值
2. **风险权重过高** - 调整`scoring_weights.yaml`中的权重
3. **误报** - 某些risk被错误识别，需要调整`risk_rules.yaml`

**解决方案**：
```bash
# 1. 查看详细风险
python -m intelligent_editor.main page.json

# 2. 检查level4_all_risks，确认哪些是误报

# 3. 调整策略（使用aggressive策略）
python -m intelligent_editor.main page.json --strategy aggressive
```

### Q2: 如何提高APPROVE的概率？

**A**:

1. **降低风险阈值** - 调整`decision_strategy.yaml`
2. **降低扣分权重** - 调整`scoring_weights.yaml`
3. **优化parser参数** - 减少源头的issues/anomalies

### Q3: Top问题为空是怎么回事？

**A**: 可能的原因：

1. **版面质量很好** - 所有风险都是LOW级别，被过滤掉了
2. **决策是APPROVE** - 只显示HIGH和MEDIUM风险，如果全是LOW则不显示
3. **决策是REJECT** - 只显示CRITICAL风险，如果没有则不显示

**解决方案**：
```bash
# 查看完整风险列表
python -m intelligent_editor.main page.json
# 查看level4_all_risks
```

### Q4: 如何批量处理多个PDF？

**A**:

```python
from pathlib import Path
from intelligent_editor.main import audit_layout

pdf_dir = Path("path/to/structured_jsons")

for json_file in pdf_dir.glob("*.json"):
    output_dir = f"results/{json_file.stem}"
    audit_layout(str(json_file), strategy='balanced', output_dir=output_dir)
```

### Q5: 如何集成到现有工作流？

**A**:

```bash
# 1. Parser阶段
python -m parser.main newspaper.pdf --output-dir parser_output

# 2. 智能审校阶段
python -m intelligent_editor.main parser_output/json/page_1_structured.json --output-dir audit_results

# 3. 查看决策
cat audit_results/audit_summary.txt
```

---

## 最佳实践

### 1. 定期校准系统

根据实际使用情况，定期调整配置文件：

```bash
# 1. 收集反馈
# 2. 统计误报率和漏报率
# 3. 调整decision_strategy.yaml的阈值
# 4. 调整scoring_weights.yaml的权重
```

### 2. 选择合适的策略

| 场景 | 推荐策略 |
|------|---------|
| 重大事件、头版 | conservative |
| 日常审版 | balanced |
| 快速审稿、紧急版面 | aggressive |

### 3. 结合人工判断

系统是决策支持工具，最终决策仍需总编辑判断：

```bash
# 1. 查看决策摘要
python -m intelligent_editor.main page.json --summary-only

# 2. 如果是REVIEW或REJECT，查看Top问题
cat editor_results/audit_summary.txt

# 3. 人工确认
# - 如果Top问题确实是问题 → 修改版面后重新提交
# - 如果是误报 → 记录下来，用于校准系统
```

### 4. 版面质量优化建议

根据系统反馈优化版面质量：

1. **减少CRITICAL风险** - 确保每篇文章都有headline
2. **减少HIGH风险** - 优化分栏，避免栏数过多
3. **提高评分** - 减少各类风险，提升基础质量

---

## 故障排除

### 问题1：运行出错 "FileNotFoundError"

**原因**：输入文件路径不正确

**解决方案**：
```bash
# 检查文件是否存在
ls -la path/to/structured.json

# 使用绝对路径
python -m intelligent_editor.main /full/path/to/structured.json
```

### 问题2：运行出错 "Invalid JSON file"

**原因**：输入文件不是有效的JSON格式

**解决方案**：
```bash
# 验证JSON格式
python -m json.tool path/to/structured.json

# 确保是parser输出的structured.json，不是raw_blocks.json
```

### 问题3：输出全是N/A

**原因**：parser输出格式不完整

**解决方案**：
```bash
# 检查structured.json是否包含所有必需字段
# 必需字段：blocks, articles, font_profile
```

### 问题4：处理时间过长

**原因**：PDF页数过多或系统资源不足

**解决方案**：
```bash
# 分批处理
python -m intelligent_editor.main page_1.json
python -m intelligent_editor.main page_2.json
```

### 问题5：决策不符合预期

**原因**：配置参数需要调整

**解决方案**：
```bash
# 1. 尝试不同策略
python -m intelligent_editor.main page.json --strategy aggressive

# 2. 查看详细风险
python -m intelligent_editor.main page.json
# 查看level4_all_risks

# 3. 调整配置
# 编辑intelligent_editor/config/*.yaml
```

---

## 📞 获取帮助

### 文档

- [完整README](INTELLIGENT_EDITOR_README.md)
- [开发文档](DEVELOPMENT.md)
- [Phase完成总结](PHASE*.md)

### 反馈渠道

如有问题或建议，请：
1. 记录问题详情
2. 保存输入文件和输出文件
3. 提交Issue到项目仓库

---

**版本**: v1.0.0
**更新时间**: 2026-03-19
**作者**: 黄帮主
