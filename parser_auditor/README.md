# Parser Auditor - PDF解析结果质量评估工具

## 功能概述

Parser Auditor是对报纸PDF解析结果进行质量评估的工具，可以：

- ✅ 计算详细的质量指标（block/article/column/zone）
- ✅ 检测结构异常和不合理之处
- ✅ 生成0-100分的质量评分
- ✅ 提供改进建议
- ✅ 输出JSON和人类可读报告

## 安装

该工具是parser_auditor模块，已包含在项目中，无需额外安装。

## 使用方法

### 基本用法

```bash
# 评估解析结果
python -m parser_auditor.main test_output/batch_20260318_160237/B2026-03-18要闻一版01/json/page_1_structured.json

# 指定输出目录
python -m parser_auditor.main page_1_structured.json --output-dir audit_results

# 只显示分数
python -m parser_auditor.main page_1_structured.json --score-only

# 安静模式（只输出分数）
python -m parser_auditor.main page_1_structured.json --quiet
```

### Python API

```python
from parser_auditor import MetricsCalculator, HeuristicsChecker, AnomalyDetector, ReportGenerator
import json

# 加载解析结果
with open('page_1_structured.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. 计算指标
metrics_calculator = MetricsCalculator(data)
metrics = metrics_calculator.calculate_all_metrics()

# 2. 启发式检查
heuristics_checker = HeuristicsChecker(data)
issues = heuristics_checker.check_all()

# 3. 异常检测
anomaly_detector = AnomalyDetector(data)
anomalies = anomaly_detector.detect_all()

# 4. 生成报告
report_generator = ReportGenerator(metrics, issues, anomalies)
report = report_generator.generate_report()

# 查看结果
print(f"Score: {report['score']}/100")
print(f"Confidence: {report['confidence']}")
```

## 输出格式

### audit_report.json

```json
{
  "score": 85,
  "score_breakdown": {
    "block_quality": 25,
    "article_quality": 30,
    "column_quality": 18,
    "zone_quality": 8,
    "global_quality": 9
  },
  "confidence": "high",
  "metrics": {
    "blocks": {...},
    "articles": {...},
    "columns": {...},
    "zones": {...},
    "global": {...}
  },
  "issues": {
    "total_issues": 2,
    "total_anomalies": 0,
    "by_severity": {
      "medium": [...],
      "low": [...]
    }
  },
  "suggestions": [
    "整体质量良好，未发现明显问题"
  ]
}
```

### audit_report.txt

人类可读的文本报告，包含：
- 总体评估（分数、置信度）
- 分数细项
- 问题汇总
- 关键指标
- 改进建议

## 评分系统

### 总分计算

总分 = Block质量(25) + Article质量(35) + Column质量(20) + Zone质量(10) + 全局质量(10)

### Block质量 (25分)

- ✅ 有headline: 0分
- ✅ 有body: 0分
- ✅ 分类一致性 ≥80%: 0分
- 否则扣分

### Article质量 (35分)

- ✅ Headline覆盖率 ≥80%: 满分
- 否则扣分 = (1 - 覆盖率) × 15
- 低置信度文章扣分 = 比例 × 10
- 平均body < 3: 扣10分

### Column质量 (20分)

- ✅ 栏数在4-10: 满分或接近满分
- 没有分栏或栏数>15: 扣10分
- 栏数<4或>10: 扣5分
- 窄栏扣分 = 数量 × 2

### Zone质量 (10分)

- headline_zone有headline: 满分
- 否则扣3分

### 全局质量 (10分)

- 阅读顺序完整性 <90%: 扣3分
- 字体清晰度poor: 扣3分

## 置信度等级

| 分数 | 异常情况 | 置信度 |
|------|----------|--------|
| ≥80 | 无critical，≤1个high | **high** |
| ≥60 | 无critical | **medium** |
| <60 | 有critical或多个high | **low** |

## 检测的问题类型

### Block级别
- `empty_block`: 空block
- `abnormal_font_size`: 字号异常
- `classification_mismatch`: 分类不一致

### Article级别
- `missing_headline`: 缺少headline
- `too_few_body_blocks`: body blocks过少
- `oversized_article`: 文章过大

### Column级别
- `too_many_columns`: 栏数过多
- `narrow_column`: 窄栏
- `wide_column`: 宽栏
- `column_crosses_zones`: 栏跨zone

### Zone级别
- `zone_without_headline`: zone没有headline
- `overpopulated_zone`: zone blocks过多

### 全局级别
- `no_headlines`: 页面没有headline
- `no_articles`: 没有文章
- `section_label_overfire`: section_label过多

## 示例

### 示例1：评估高质量解析结果

```bash
$ python -m parser_auditor.main output_global_columns/json/page_1_structured.json
============================================================
PDF解析结果质量评估
============================================================
Score: 85/100
Confidence: HIGH
Issues: 0
Anomalies: 0
============================================================
```

### 示例2：检测到问题

```bash
$ python -m parser_auditor.main page_1_structured.json
Score: 65/100
Confidence: MEDIUM
Issues: 3
Anomalies: 1

【改进建议】
1. 建议调整分栏检测参数，可能存在分栏不合理
2. 有1篇文章缺少headline，建议检查article_builder的headline匹配逻辑
```

## 贡献

欢迎提交Issue和Pull Request！
