# 智能审校系统 - 开发文档

**Intelligent Editor System - Development Guide**

---

## 📖 目录

1. [架构设计](#架构设计)
2. [模块职责](#模块职责)
3. [数据流](#数据流)
4. [扩展指南](#扩展指南)
5. [测试指南](#测试指南)
6. [编码规范](#编码规范)
7. [性能优化](#性能优化)
8. [常见开发任务](#常见开发任务)

---

## 架构设计

### 系统定位

智能审校系统是一个**决策支持系统**，而非传统的校对工具。

**核心目标**：
- 3秒内输出approve/reject/review决策
- 识别影响付印的风险（risks），而非列出所有错误（issues）
- 提供可解释的判断依据

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Input Layer                              │
│  parser_auditor输出: structured.json + issues + anomalies    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Intelligent Editor                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ RiskEngine   │→ │ScoringEngine │→ │DecisionEngine│      │
│  │ 风险识别      │  │ 评分计算     │  │ 决策生成     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │Explanation   │← │TopIssues     │                         │
│  │Engine        │  │Extractor     │                         │
│  │ 解释生成      │  │ 问题提取     │                         │
│  └──────────────┘  └──────────────┘                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Output Layer                              │
│  5层输出结构: Decision → Score → Top Issues → All Risks     │
│              → Explanation                                   │
└─────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **风险优先（Risk > Error）**
   - 不追求完美检测所有错误
   - 关注影响付印的风险
   - 允许误报，不能漏报critical风险

2. **输出结论优先**
   - Level 1决策层优先输出
   - 总编辑只看decision + risk_level
   - 详细信息在后续层级

3. **信息压缩**
   - 默认只显示Top 3问题
   - 避免信息过载
   - 按需查看完整风险列表

4. **配置驱动**
   - 所有规则在YAML文件中
   - 易于调整和优化
   - 无需修改代码

5. **可解释性**
   - 所有判断都有reasoning
   - 每个风险都有impact说明
   - 自然语言生成

---

## 模块职责

### 1. RiskEngine（风险识别引擎）

**文件**: `intelligent_editor/core/risk_engine.py`

**职责**:
- 将parser_auditor的issues转化为risks
- 将parser_auditor的anomalies转化为risks
- 风险聚合和去重
- 按severity排序

**核心方法**:
```python
def identify_risks(
    issues: List[Dict],
    anomalies: Dict[str, List[Dict]],
    metrics: Dict
) -> List[Risk]:
    """
    主入口：识别所有风险

    流程:
    1. issues → risks（基于risk_rules.yaml映射）
    2. anomalies → risks
    3. 风险聚合和去重
    4. 按severity排序
    """
```

**关键逻辑**:
- Issue到Risk的映射：`issue_mappings`配置
- Severity计算：基于issue severity和risk_rules
- 风险聚合：同类型风险最多保留N个

**配置依赖**:
- `risk_rules.yaml`: issue_mappings, severity_rules, aggregation_rules

---

### 2. DecisionEngine（决策引擎）

**文件**: `intelligent_editor/core/decision_engine.py`

**职责**:
- 基于risks输出approve/reject/review决策
- 计算风险等级（CRITICAL/HIGH/MEDIUM/LOW）
- 计算置信度
- 生成决策依据

**核心方法**:
```python
def make_decision(
    risks: List[Risk],
    metrics: Dict,
    strategy: str = 'balanced'
) -> Decision:
    """
    主入口：做出版面决策

    流程:
    1. 统计各级风险数量
    2. 计算风险等级
    3. 应用决策策略阈值
    4. 计算置信度
    5. 生成决策依据
    """
```

**关键逻辑**:
- 风险等级计算规则：
  - CRITICAL: 有任何critical风险
  - HIGH: ≥2个high 或 ≥5个medium
  - MEDIUM: 1个high 或 2-4个medium
  - LOW: 其他

- 决策规则（balanced策略）：
  - APPROVE: C=0, H≤1, M≤3
  - REVIEW: C=0, H≤2, M≤5
  - REJECT: 其他

**配置依赖**:
- `decision_strategy.yaml`: strategies, thresholds, reasoning_templates

---

### 3. ScoringEngine（评分引擎）

**文件**: `intelligent_editor/core/scoring_engine.py`

**职责**:
- 基于risks生成0-100评分
- 计算质量等级（A/B/C/D/F）
- 生成分数细项

**核心方法**:
```python
def calculate_score(
    risks: List[Risk],
    metrics: Dict
) -> Score:
    """
    主入口：计算版面质量评分

    流程:
    1. 基础分（来自parser_auditor）
    2. 风险扣分
    3. 加分项（无风险奖励）
    4. 最终分数
    5. 质量等级
    """
```

**关键逻辑**:
- 风险扣分权重：
  - CRITICAL: -30分
  - HIGH: -15分
  - MEDIUM: -5分
  - LOW: -1分
  - 最多扣50分

- 加分规则：
  - 无CRITICAL: +5分
  - 无HIGH: +3分
  - 完美无风险: +10分

- 质量等级：
  - A: 90-100
  - B: 80-89
  - C: 70-79
  - D: 60-69
  - F: 0-59

**配置依赖**:
- `scoring_weights.yaml`: risk_weights, max_penalty, bonus_rules, grade_thresholds

---

### 4. TopIssuesExtractor（Top问题提取器）

**文件**: `intelligent_editor/core/top_issues_extractor.py`

**职责**:
- 从risks中筛选Top 3最重要的问题
- 信息压缩
- 生成summary和action_needed

**核心方法**:
```python
def extract_top_issues(
    risks: List[Risk],
    decision: Decision
) -> List[TopIssue]:
    """
    主入口：提取Top 3问题

    流程:
    1. 根据decision类型过滤风险
    2. 按severity排序
    3. 聚合同类型风险
    4. 生成summary（≤20字）
    5. 生成action_needed（≤15字）
    6. 选择Top 3
    """
```

**关键逻辑**:
- 过滤规则：
  - REJECT: 只显示CRITICAL
  - REVIEW: 显示CRITICAL + HIGH
  - APPROVE: 显示HIGH + MEDIUM

- Summary生成：
  - 提取关键信息（类型+受影响元素）
  - 限制≤20字

- Action_needed生成：
  - 基于fix_suggestion
  - 限制≤15字

---

### 5. ExplanationEngine（解释引擎）

**文件**: `intelligent_editor/core/explanation_engine.py`

**职责**:
- 为决策生成自然语言解释
- 为风险等级生成解释
- 为评分生成解释
- 为问题优先级生成解释
- 为置信度生成解释

**核心方法**:
```python
def generate_explanation(
    decision: Decision,
    score: Score,
    top_issues: List[TopIssue],
    risks: List[Risk]
) -> Explanation:
    """
    主入口：生成完整解释

    流程:
    1. 决策解释
    2. 风险等级解释
    3. 评分解释
    4. 问题优先级解释
    5. 置信度解释
    """
```

**关键逻辑**:
- 模板填充：使用explanation_templates.yaml
- 动态生成：根据风险统计生成个性化解释
- 多层次：简短版+详细版

**配置依赖**:
- `explanation_templates.yaml`: 所有解释模板

---

### 6. ConfigLoader（配置加载器）

**文件**: `intelligent_editor/utils/config_loader.py`

**职责**:
- 加载YAML配置文件
- 验证配置完整性
- 提供配置访问接口

**核心方法**:
```python
@staticmethod
def load_config(config_name: str) -> Dict[str, Any]:
    """
    加载配置文件

    Args:
        config_name: risk_rules / decision_strategy / scoring_weights / explanation_templates

    Returns:
        配置字典
    """
```

---

## 数据流

### 完整数据流

```
1. 输入阶段
   ┌─────────────┐
   │ structured.json
   │ (parser输出)
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │ parser_auditor
   │              │
   │ - issues     │
   │ - anomalies  │
   │ - metrics    │
   └──────┬──────┘
          │
          ▼

2. 风险识别阶段
   ┌─────────────┐
   │ RiskEngine  │
   │              │
   │ issues → risks
   │ anomalies →
   │   risks      │
   └──────┬──────┘
          │
          ▼
   List[Risk]

3. 评分阶段
   ┌─────────────┐
   │ScoringEngine│
   │              │
   │ risks → score│
   └──────┬──────┘
          │
          ▼
   Score

4. 决策阶段
   ┌─────────────┐
   │DecisionEngine│
   │              │
   │ risks →      │
   │   decision   │
   └──────┬──────┘
          │
          ▼
   Decision

5. Top问题提取
   ┌─────────────┐
   │TopIssues    │
   │Extractor    │
   │              │
   │ risks →      │
   │   top_issues │
   └──────┬──────┘
          │
          ▼
   List[TopIssue]

6. 解释生成
   ┌─────────────┐
   │Explanation  │
   │Engine       │
   │              │
   │ decision →   │
   │   explanation│
   └──────┬──────┘
          │
          ▼
   Explanation

7. 输出阶段
   ┌─────────────┐
   │ 5层报告     │
   │              │
   │ - Level 1:   │
   │   decision   │
   │ - Level 2:   │
   │   score      │
   │ - Level 3:   │
   │   top_issues │
   │ - Level 4:   │
   │   all_risks  │
   │ - Level 5:   │
   │   explanation│
   └─────────────┘
```

### 数据结构关系

```
Risk (风险)
├── id: str
├── type: str
├── severity: Severity (CRITICAL/HIGH/MEDIUM/LOW)
├── source: str ('issue' or 'anomaly')
├── description: str
├── affected_elements: List[str]
├── impact: str
└── confidence: float

Decision (决策)
├── type: DecisionType (APPROVE/REVIEW/REJECT)
├── risk_level: RiskLevel (CRITICAL/HIGH/MEDIUM/LOW)
├── confidence: float
├── reasoning: str
├── critical_risks: List[Risk]
└── high_risks: List[Risk]

Score (评分)
├── total_score: float
├── quality_grade: str (A/B/C/D/F)
├── base_score: float
├── risk_penalty: float
├── bonus: float
└── breakdown: Dict

TopIssue (Top问题)
├── rank: int (1/2/3)
├── risk: Risk
├── summary: str (≤20字)
└── action_needed: str (≤15字)

Explanation (解释)
├── decision_explanation: str
├── decision_short: str
├── risk_level_explanation: str
├── score_explanation: str
├── top_issues_explanation: str
└── confidence_explanation: str
```

---

## 扩展指南

### 添加新的风险类型

**场景**: 需要识别一种新的风险类型

**步骤**:

1. **在risk_rules.yaml中添加映射**

```yaml
issue_mappings:
  # 新增
  new_issue_type: high_article_risk

severity_rules:
  high:
    threshold: 3
    description: "严重影响版面质量"
    requires_rejection: false
```

2. **在RiskEngine中添加修复建议（可选）**

```python
# 在risk_engine.py的_generate_fix_suggestion中添加
suggestions = {
    # 新增
    'new_issue_type': '检查XXX逻辑',
}
```

3. **在scoring_weights.yaml中配置权重（如果需要自定义权重）**

```yaml
risk_weights:
  HIGH: 15  # 新风险类型会使用HIGH的权重
```

### 添加新的决策策略

**场景**: 需要一种新的决策策略（如"超级保守"）

**步骤**:

1. **在decision_strategy.yaml中添加策略配置**

```yaml
strategies:
  ultra_conservative:  # 新策略名
    description: "超级保守策略"
    thresholds:
      approve:
        max_critical: 0
        max_high: 0
        max_medium: 0  # 比conservative更严格
      review:
        max_critical: 0
        max_high: 0
        max_medium: 1
    reasoning_templates:
      approve:
        short: "版面质量优秀，可以付印"
        detailed: "版面质量评估为{grade}级..."
```

2. **在CLI中使用**

```bash
python -m intelligent_editor.main page.json --strategy ultra_conservative
```

### 自定义评分规则

**场景**: 需要调整评分算法

**步骤**:

1. **修改scoring_weights.yaml**

```yaml
# 调整风险扣分权重
risk_weights:
  CRITICAL: 40  # 从30改为40
  HIGH: 20      # 从15改为20

# 调整等级阈值
grade_thresholds:
  A: 95  # 从90改为95
  B: 85
```

2. **如果需要更复杂的算法，修改ScoringEngine**

```python
# 在scoring_engine.py中添加新的计算逻辑
def _calculate_custom_penalty(self, risks: List[Risk]) -> float:
    """自定义扣分算法"""
    # 实现你的逻辑
    pass
```

### 添加新的解释模板

**场景**: 需要更个性化的解释文本

**步骤**:

1. **修改explanation_templates.yaml**

```yaml
decision_templates:
  approve:
    short: "质量优秀，建议付印"
    detailed: "经评估，版面质量达到{grade}级标准..."
```

2. **如需新增解释维度，修改ExplanationEngine**

```python
# 添加新的解释方法
def explain_custom_dimension(self, ...) -> str:
    """自定义解释维度"""
    pass
```

---

## 测试指南

### 单元测试

**测试RiskEngine**

```python
# tests/test_risk_engine.py
import pytest
from intelligent_editor.core import RiskEngine
from intelligent_editor.models import Severity

def test_convert_issues_to_risks():
    """测试issue转换为risk"""
    # 配置
    risk_config = ConfigLoader.load_config('risk_rules')
    engine = RiskEngine(risk_config)

    # 测试数据
    issues = [
        {'type': 'missing_headline', 'severity': 'critical', 'article_id': 'a1'},
    ]

    # 执行
    risks = engine._convert_issues_to_risks(issues)

    # 断言
    assert len(risks) == 1
    assert risks[0].severity == Severity.CRITICAL
    assert risks[0].type == 'critical_article_risk'

def test_aggregate_risks():
    """测试风险聚合"""
    risk_config = ConfigLoader.load_config('risk_rules')
    engine = RiskEngine(risk_config)

    # 创建10个同类型风险
    risks = [create_risk('same_type') for _ in range(10)]

    # 执行聚合
    aggregated = engine._aggregate_risks(risks)

    # 断言：最多保留3个
    assert len(aggregated) <= 3
```

**测试DecisionEngine**

```python
# tests/test_decision_engine.py
def test_approve_decision():
    """测试APPROVE决策"""
    decision_config = ConfigLoader.load_config('decision_strategy')
    engine = DecisionEngine(decision_config)

    # 创建低风险场景
    risks = [
        create_risk(severity=Severity.LOW),
        create_risk(severity=Severity.LOW),
    ]

    # 执行
    decision = engine.make_decision(risks, {}, strategy='balanced')

    # 断言
    assert decision.type == DecisionType.APPROVE
    assert decision.risk_level == RiskLevel.LOW

def test_reject_decision():
    """测试REJECT决策"""
    decision_config = ConfigLoader.load_config('decision_strategy')
    engine = DecisionEngine(decision_config)

    # 创建高风险场景
    risks = [
        create_risk(severity=Severity.CRITICAL),
    ]

    # 执行
    decision = engine.make_decision(risks, {}, strategy='balanced')

    # 断言
    assert decision.type == DecisionType.REJECT
    assert decision.risk_level == RiskLevel.CRITICAL
```

**测试ScoringEngine**

```python
# tests/test_scoring_engine.py
def test_calculate_score():
    """测试评分计算"""
    scoring_config = ConfigLoader.load_config('scoring_weights')
    engine = ScoringEngine(scoring_config)

    # 创建风险
    risks = [
        create_risk(severity=Severity.HIGH),  # -15分
        create_risk(severity=Severity.MEDIUM), # -5分
    ]

    # 执行
    score = engine.calculate_score(risks, {'score': 85})

    # 断言
    assert score.total_score == 85 - 15 - 5
    assert score.quality_grade == 'B'  # 假设65分对应B级

def test_perfect_score():
    """测试完美评分"""
    scoring_config = ConfigLoader.load_config('scoring_weights')
    engine = ScoringEngine(scoring_config)

    # 无风险
    score = engine.calculate_score([], {'score': 85})

    # 断言：基础分 + 完美奖励
    assert score.total_score == 85 + 10
    assert score.bonus == 10
```

### 集成测试

**测试完整流程**

```python
# tests/test_integration.py
def test_full_pipeline():
    """测试完整流程"""
    # 准备测试数据
    structured_json = load_test_data('test_structured.json')

    # 执行
    report = audit_layout(
        json_path='test_structured.json',
        strategy='balanced',
        output_dir='test_output'
    )

    # 验证5层输出
    assert 'level1_decision' in report
    assert 'level2_score' in report
    assert 'level3_top_issues' in report
    assert 'level4_all_risks' in report
    assert 'level5_explanation' in report

    # 验证决策
    assert report['level1_decision']['decision'] in ['approve', 'review', 'reject']
```

### 性能测试

```python
# tests/test_performance.py
import time

def test_processing_time():
    """测试处理时间"""
    start = time.time()

    report = audit_layout('large_structured.json')

    elapsed = time.time() - start

    # 断言：处理时间 < 3秒
    assert elapsed < 3.0
    print(f"Processing time: {elapsed:.2f}s")

def test_memory_usage():
    """测试内存使用"""
    import tracemalloc

    tracemalloc.start()

    report = audit_layout('large_structured.json')

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 断言：峰值内存 < 500MB
    assert peak < 500 * 1024 * 1024
    print(f"Peak memory: {peak / 1024 / 1024:.1f}MB")
```

### 测试数据准备

**创建测试数据集**

```bash
# 测试数据目录结构
tests/
├── data/
│   ├── good_layout.json          # 高质量版面（应该APPROVE）
│   ├── problematic_layout.json   # 有问题的版面（应该REVIEW）
│   ├── critical_layout.json      # 重大风险版面（应该REJECT）
│   └── large_layout.json         # 大型版面（性能测试）
├── test_risk_engine.py
├── test_decision_engine.py
├── test_scoring_engine.py
├── test_explanation_engine.py
└── test_integration.py
```

---

## 编码规范

### Python代码规范

**遵循PEP 8标准**

```python
# 好的示例
class RiskEngine:
    """
    风险识别引擎

    将issues/anomalies转化为risks
    """

    def identify_risks(
        self,
        issues: List[Dict],
        anomalies: Dict[str, List[Dict]],
        metrics: Dict
    ) -> List[Risk]:
        """
        识别所有风险

        Args:
            issues: HeuristicsChecker的输出
            anomalies: AnomalyDetector的输出
            metrics: MetricsCalculator的输出

        Returns:
            Risk对象列表，按severity排序
        """
        risks = []

        # 逻辑清晰，注释充分
        for issue in issues:
            risk = self._convert_issue_to_risk(issue)
            risks.append(risk)

        return risks
```

**命名规范**

- 类名：PascalCase（如`RiskEngine`）
- 函数/方法：snake_case（如`identify_risks`）
- 常量：UPPER_SNAKE_CASE（如`MAX_PENALTY`）
- 私有方法：前缀下划线（如`_convert_issue_to_risk`）

**类型注解**

```python
from typing import List, Dict, Optional

def calculate_score(
    risks: List[Risk],
    metrics: Dict[str, Any]
) -> Score:
    """所有公共方法必须有类型注解"""
    pass

def _private_helper(
    value: int
) -> Optional[str]:
    """私有方法也需要类型注解"""
    pass
```

### 文档字符串规范

**Google Style Docstrings**

```python
def make_decision(
    self,
    risks: List[Risk],
    metrics: Dict,
    strategy: str = None
) -> Decision:
    """
    做出版面决策

    基于risks和metrics，应用指定策略，输出approve/reject/review决策。

    Args:
        risks: 风险列表，来自RiskEngine
        metrics: 质量指标，来自parser_auditor
        strategy: 决策策略名称（conservative/balanced/aggressive）

    Returns:
        Decision对象，包含决策类型、风险等级、置信度等

    Raises:
        ValueError: 如果strategy名称无效

    Examples:
        >>> engine = DecisionEngine(config)
        >>> decision = engine.make_decision(risks, metrics, 'balanced')
        >>> print(decision.type)
        'approve'
    """
```

### 日志规范

```python
import logging

logger = logging.getLogger("intelligent_editor")

# 日志级别使用
logger.debug("详细调试信息")  # 开发时使用
logger.info("关键步骤信息")   # 正常运行时使用
logger.warning("警告信息")    # 需要关注但不影响运行
logger.error("错误信息")     # 错误但可以继续
logger.critical("严重错误")  # 无法继续运行

# 日志格式
logger.info(f"Decision made: {decision_type.value} (confidence={confidence:.1%})")
logger.info(f"Total risks identified: {len(risks)}")
```

### 错误处理规范

```python
# 主动验证输入
def identify_risks(self, issues, anomalies, metrics):
    if not isinstance(issues, list):
        raise TypeError(f"issues must be list, got {type(issues)}")

    if issues is None:
        logger.warning("issues is None, returning empty risks")
        return []

    # 使用try-except处理外部依赖
    try:
        risks = self._convert_issues_to_risks(issues)
    except Exception as e:
        logger.error(f"Failed to convert issues to risks: {e}")
        raise
```

---

## 性能优化

### 当前性能指标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 处理时间 | < 3秒 | 0.01秒 | ✅ 远超目标 |
| 内存占用 | < 500MB | ~100MB | ✅ 符合预期 |
| 风险覆盖率 | 100% | 100% | ✅ |

### 优化建议

**1. 风险聚合优化**

```python
# 当前实现
def _aggregate_risks(self, risks: List[Risk]) -> List[Risk]:
    # 按类型分组
    risk_groups = defaultdict(list)
    for risk in risks:
        risk_groups[risk.type].append(risk)

    # 优化：使用生成器减少内存
    aggregated_risks = []
    for risk_type, risk_list in risk_groups.items():
        # 只排序前N个，而非全部
        top_risks = nlargest(max_per_type, risk_list, key=lambda r: r.severity_score)
        aggregated_risks.extend(top_risks)

    return aggregated_risks
```

**2. 配置缓存**

```python
# 在ConfigLoader中添加缓存
from functools import lru_cache

@lru_cache(maxsize=10)
@staticmethod
def load_config(config_name: str) -> Dict[str, Any]:
    """加载配置文件，使用LRU缓存"""
    # 实现不变
    pass
```

**3. 延迟计算**

```python
# 只在需要时计算详细信息
class Decision:
    def __init__(self, ...):
        self._detailed_analysis = None

    @property
    def detailed_analysis(self):
        """延迟计算详细分析"""
        if self._detailed_analysis is None:
            self._detailed_analysis = self._compute_detailed_analysis()
        return self._detailed_analysis
```

---

## 常见开发任务

### 任务1: 添加新的issue类型映射

**场景**: parser_auditor添加了新的issue检测

**步骤**:

1. 在`risk_rules.yaml`中添加映射
2. （可选）添加修复建议
3. 测试新issue的识别和决策

**文件**:
- `intelligent_editor/config/risk_rules.yaml`

---

### 任务2: 调整决策阈值

**场景**: 需要更严格或更宽松的决策标准

**步骤**:

1. 修改`decision_strategy.yaml`中的thresholds
2. 测试不同场景下的决策结果
3. 根据测试结果微调

**文件**:
- `intelligent_editor/config/decision_strategy.yaml`

---

### 任务3: 优化解释文本

**场景**: 用户反馈解释不够清晰

**步骤**:

1. 修改`explanation_templates.yaml`中的模板
2. 测试不同场景下的解释生成
3. 确保语言专业、清晰、客观

**文件**:
- `intelligent_editor/config/explanation_templates.yaml`

---

### 任务4: 添加新的输出格式

**场景**: 需要输出HTML或Markdown格式

**步骤**:

1. 在`main.py`中添加新的输出格式处理
2. 创建formatter类
3. 添加CLI参数（如`--format html`）

**文件**:
- `intelligent_editor/main.py`
- `intelligent_editor/utils/formatters.py`（新建）

---

### 任务5: 增强错误处理

**场景**: 需要更友好的错误提示

**步骤**:

1. 在`main.py`中添加try-except块
2. 定义自定义异常类
3. 添加错误码和错误消息映射

**文件**:
- `intelligent_editor/exceptions.py`（新建）
- `intelligent_editor/main.py`

---

## 📚 参考资料

### 内部文档

- [用户使用指南](intelligent_editor/USER_GUIDE.md)
- [系统README](INTELLIGENT_EDITOR_README.md)
- [Phase完成总结](PHASE*.md)

### 外部依赖

- [PyYAML文档](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [typing模块](https://docs.python.org/3/library/typing.html)

### 设计模式

- **策略模式**: DecisionEngine使用不同决策策略
- **工厂模式**: ConfigLoader创建配置对象
- **模板方法**: 各Engine的基类定义处理流程

---

## 🤝 贡献指南

### 提交代码

1. 遵循编码规范
2. 添加单元测试
3. 更新文档
4. 提交PR前运行完整测试

### 报告问题

1. 提供详细的复现步骤
2. 附上输入数据和期望输出
3. 包含日志和错误信息

---

**版本**: v1.0.0
**更新时间**: 2026-03-19
**作者**: 黄帮主
