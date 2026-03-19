# 总编辑审校系统重构方案（Phase 1）

## 目标

把当前“规则问题堆叠式报告”升级为面向总编辑的分层系统：

1. 版面工程底线层
2. 总编辑安全评估层
3. 总编辑优化决策层

Phase 1 先完成模块边界、数据模型、报告分层和兼容接入，不在这一阶段强依赖大模型。

## 新版模块设计

### 1. 工程底线层

职责：
- 保留 parser / parser_auditor / 版面工程规则能力
- 识别分栏、聚类、缺标题、块分类等底线问题
- 作为总编辑报告附录，不再占主结论

核心模块：
- `intelligent_editor/core/risk_engine.py`
- `intelligent_editor/core/decision_engine.py`
- `intelligent_editor/core/top_issues_extractor.py`

### 2. 安全评估层

职责：
- 统一承接总编辑安全判断
- 当前阶段先做“规则底稿 + 人工复核提醒”骨架
- 下一阶段接入大模型做导向、政治表达、口径一致性判断

新增模块：
- `intelligent_editor/core/safety_evaluator.py`

输出：
- `SafetyReport`

### 3. 优化决策层

职责：
- 把“问题列表”升级成“编辑任务”
- 聚合成总编辑最值得改的 1 到 3 个任务
- 为每个任务补充可执行选项

新增模块：
- `intelligent_editor/core/editorial_optimizer.py`
- `intelligent_editor/core/candidate_guardrail.py`

输出：
- `OptimizationTask`
- `OptimizationReport`

### 4. 分层报告模型

新增模型：
- `EngineeringBaselineReport`
- `SafetyFinding`
- `SafetyReport`
- `OptimizationOption`
- `OptimizationTask`
- `OptimizationReport`
- `ExecutiveAuditReport`

文件：
- `intelligent_editor/models/executive_report.py`

## 文件改造清单

### 新增

- `K:\Work\大样审校\intelligent_editor\models\executive_report.py`
- `K:\Work\大样审校\intelligent_editor\core\safety_evaluator.py`
- `K:\Work\大样审校\intelligent_editor\core\editorial_optimizer.py`
- `K:\Work\大样审校\intelligent_editor\core\candidate_guardrail.py`
- `K:\Work\大样审校\intelligent_editor\prompts\safety_prompt.md`
- `K:\Work\大样审校\intelligent_editor\prompts\optimizer_prompt.md`

### 修改

- `K:\Work\大样审校\intelligent_editor\main_v2.py`
  - 接入新版层级评估
  - 输出安全报告、优化报告、分层 JSON
- `K:\Work\大样审校\intelligent_editor\models\__init__.py`
  - 导出新模型
- `K:\Work\大样审校\intelligent_editor\core\__init__.py`
  - 导出新执行器
- `K:\Work\大样审校\tests\test_end_to_end_reports.py`
  - 校验新版报告文件与关键字段
- `K:\Work\大样审校\tests\test_contracts.py`
  - 校验优化任务聚合与安全层骨架

## 分阶段实施

### Phase 1

- 搭建新模型
- 搭建安全评估/优化决策骨架
- 主报告改成“安全报告 + 优化报告 + 底线附录”
- 保留旧返回接口兼容测试

### Phase 2

- 接入 LLM 安全评估
- 接入 LLM 编辑改写任务生成
- 引入候选方案守卫规则

### Phase 3

- 加人工复核闭环
- 建立安全与优化对照评估集
- 调整排序、提示和报告呈现
