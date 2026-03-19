import unittest
from pathlib import Path

from intelligent_editor.core.editorial_optimizer import EditorialOptimizer
from intelligent_editor.core.headline_analyzer import HeadlineAnalyzer
from intelligent_editor.core.editorial_quality_engine import EditorialQualityEngine
from intelligent_editor.core.lead_analyzer import LeadAnalyzer
from intelligent_editor.core.optimization_engine import OptimizationEngine
from intelligent_editor.core.risk_engine import RiskEngine
from intelligent_editor.core.safety_evaluator import SafetyEvaluator
from intelligent_editor.core.top_issues_extractor import TopIssuesExtractor
from intelligent_editor.evaluation import evaluate_case_files
from intelligent_editor.models.decision import Decision, DecisionType, RiskLevel
from intelligent_editor.models.risk import Risk, Severity
from parser.main import parse_page_range


class ParserContractTests(unittest.TestCase):
    def test_parse_page_range_all(self):
        self.assertEqual(parse_page_range("all", 3), [0, 1, 2])

    def test_parse_page_range_slice(self):
        self.assertEqual(parse_page_range("2-3", 5), [1, 2])

    def test_parse_page_range_single_page(self):
        self.assertEqual(parse_page_range("1", 5), [0])


class EditorContractTests(unittest.TestCase):
    def setUp(self):
        self.structured_data = {
            "width": 1000,
            "blocks": [
                {
                    "id": "h1",
                    "text": "cheng shi geng xin gong zuo quan mian tui jin",
                    "bbox": [0, 0, 300, 40],
                    "font_size": 12,
                },
                {
                    "id": "s1",
                    "text": "cheng shi geng xin",
                    "bbox": [0, 50, 200, 70],
                    "font_size": 10,
                },
                {
                    "id": "b1",
                    "text": "cheng shi geng xin xiang mu shou ci wan cheng gai zao and huan jing gai shan.",
                    "bbox": [0, 80, 300, 120],
                    "font_size": 9,
                },
                {
                    "id": "b2",
                    "text": "xiang guan gong zuo chi xu tui jin.",
                    "bbox": [0, 125, 300, 160],
                    "font_size": 9,
                },
                {
                    "id": "h2",
                    "text": "she qu fu wu zai sheng ji",
                    "bbox": [600, 0, 900, 40],
                    "font_size": 18,
                },
            ],
            "articles": [
                {
                    "id": "a1",
                    "headline_block_id": "h1",
                    "subheadline_block_id": "s1",
                    "body_block_ids": ["b1", "b2"],
                },
                {
                    "id": "a2",
                    "headline_block_id": "h2",
                    "body_block_ids": [],
                },
            ],
            "font_profile": {"headline": [12, 18, 13], "body": [8, 10, 9]},
        }

    def test_headline_analyzer_reads_blocks_from_ids(self):
        analyzer = HeadlineAnalyzer({"headline_rewrite": {"enabled": False}})
        suggestions = analyzer.analyze_headlines(self.structured_data)
        self.assertTrue(any(item.article_id == "a1" for item in suggestions))

    def test_lead_analyzer_uses_body_blocks(self):
        analyzer = LeadAnalyzer({})
        suggestions = analyzer.analyze_leads(self.structured_data)
        self.assertTrue(any(item.article_id == "a1" for item in suggestions))

    def test_optimization_engine_reads_bbox_arrays(self):
        engine = OptimizationEngine({"headline_rules": {"max_length": 20}})
        report = engine.generate_suggestions(self.structured_data, {}, [])
        self.assertGreaterEqual(report.total_count, 1)

    def test_editorial_quality_engine_generates_non_placeholder_scores(self):
        engine = EditorialQualityEngine({})
        report = engine.generate_quality_assessment(self.structured_data, {}, [])
        self.assertNotEqual(report.assessment.packaging_quality_score, 85.0)
        self.assertNotEqual(report.assessment.diversity_score, 80.0)

    def test_top_issues_extractor_keeps_high_blockers_for_reject(self):
        extractor = TopIssuesExtractor({"max_issues": 3})
        risks = [
            Risk(
                id="r1",
                type="high_layout_risk",
                severity=Severity.HIGH,
                source="issue",
                description="Too many columns detected: 17",
                fix_suggestion="调整分栏检测参数",
            ),
            Risk(
                id="r2",
                type="article_article_without_headline_risk",
                severity=Severity.HIGH,
                source="issue",
                description="Article a_right_zone_noheadline has no headline",
                affected_elements=["article_id:a_right_zone_noheadline"],
                fix_suggestion="检查article聚类逻辑",
            ),
        ]
        decision = Decision(
            type=DecisionType.REJECT,
            risk_level=RiskLevel.HIGH,
            confidence=0.6,
            reasoning="high blockers present",
        )

        top_issues = extractor.extract_top_issues(risks, decision)

        self.assertEqual(len(top_issues), 2)
        self.assertIn("a_right_zone_noheadline", top_issues[0].summary)

    def test_risk_engine_generates_unique_ids_and_normalized_types(self):
        engine = RiskEngine(
            {
                "issue_mappings": {
                    "missing_headline": "critical_article_risk",
                    "zone_without_headline": "medium_layout_risk",
                },
                "aggregation_rules": {"same_type_aggregation": False},
            }
        )
        issues = [
            {
                "type": "missing_headline",
                "severity": "high",
                "reason": "Article a1 has no headline",
                "article_id": "a1",
            }
        ]
        anomalies = {
            "article": [
                {
                    "type": "article_without_headline",
                    "severity": "high",
                    "reason": "Article a2 has no headline",
                    "article_id": "a2",
                }
            ],
            "zone": [
                {
                    "type": "zone_without_headline",
                    "severity": "high",
                    "reason": "Zone z1 has no headline",
                    "zone": "z1",
                }
            ],
        }

        risks = engine.identify_risks(issues, anomalies, {})

        self.assertEqual(len({risk.id for risk in risks}), len(risks))
        self.assertIn("critical_article_risk", {risk.type for risk in risks})
        self.assertIn("medium_layout_risk", {risk.type for risk in risks})

    def test_safety_evaluator_marks_semantic_review_pending(self):
        extractor = TopIssuesExtractor({"max_issues": 3})
        risks = [
            Risk(
                id="r1",
                type="critical_article_risk",
                severity=Severity.HIGH,
                source="issue",
                description="Article a1 has no headline",
                affected_elements=["article_id:a1"],
                fix_suggestion="补齐标题",
            )
        ]
        decision = Decision(
            type=DecisionType.REJECT,
            risk_level=RiskLevel.HIGH,
            confidence=0.8,
            reasoning="critical baseline issue",
        )
        top_issues = extractor.extract_top_issues(risks, decision)

        report = SafetyEvaluator().evaluate(decision, top_issues, risks)

        self.assertFalse(report.semantic_review_enabled)
        self.assertTrue(report.requires_manual_review)
        self.assertTrue(
            any(item.requires_manual_review for item in report.findings)
        )

    def test_safety_evaluator_uses_semantic_review_when_available(self):
        class FakeReviewer:
            def is_available(self):
                return True

            def review(self, payload):
                self.payload = payload
                return {
                    "recommendation": "review",
                    "risk_level": "MEDIUM",
                    "summary": "发现一处需要总编辑关注的表述风险。",
                    "requires_manual_review": True,
                    "note": "模型建议人工终审。",
                    "findings": [
                        {
                            "level": "HIGH",
                            "title": "关键句存在口径歧义",
                            "detail": "一处标题表达可能引发口径误读。",
                            "action": "请总编辑核定最终口径。",
                            "source": "semantic_review",
                            "requires_manual_review": True,
                        }
                    ],
                }

        extractor = TopIssuesExtractor({"max_issues": 3})
        risks = [
            Risk(
                id="r1",
                type="critical_article_risk",
                severity=Severity.HIGH,
                source="issue",
                description="Article a1 has no headline",
                affected_elements=["article_id:a1"],
                fix_suggestion="补齐标题",
            )
        ]
        decision = Decision(
            type=DecisionType.REJECT,
            risk_level=RiskLevel.HIGH,
            confidence=0.8,
            reasoning="critical baseline issue",
        )
        top_issues = extractor.extract_top_issues(risks, decision)
        reviewer = FakeReviewer()

        report = SafetyEvaluator({}, reviewer=reviewer).evaluate(
            decision,
            top_issues,
            risks,
            self.structured_data,
        )

        self.assertTrue(report.semantic_review_enabled)
        self.assertEqual(report.recommendation, "review")
        self.assertTrue(any(item.source == "semantic_review" for item in report.findings))
        self.assertEqual(reviewer.payload["articles"][0]["article_id"], "a1")

    def test_editorial_optimizer_builds_executive_tasks(self):
        quality_report = EditorialQualityEngine({}).generate_quality_assessment(
            self.structured_data,
            {},
            [],
        )

        report = EditorialOptimizer().build_report(quality_report)

        self.assertLessEqual(len(report.tasks), 3)
        self.assertTrue(any(task.task_type == "headline" for task in report.tasks))
        self.assertTrue(any(task.options for task in report.tasks))

    def test_editorial_optimizer_uses_llm_candidates_when_available(self):
        class FakeGenerator:
            def is_available(self):
                return True

            def generate(self, payload):
                return {
                    "task_title": "重点标题建议重写",
                    "summary": "给出更聚焦的标题方案。",
                    "options": [
                        {
                            "label": "方案A",
                            "content": "城市更新跑出新速度",
                            "rationale": "更聚焦结果导向。",
                            "fit_for": "适合头条",
                            "risk_note": "需核对口径",
                        },
                        {
                            "label": "方案B",
                            "content": "震惊全城的城市更新",
                            "rationale": "故意制造不合规候选",
                            "fit_for": "不应通过",
                            "risk_note": "夸张",
                        },
                    ],
                }

        quality_report = EditorialQualityEngine({}).generate_quality_assessment(
            self.structured_data,
            {},
            [],
        )

        report = EditorialOptimizer({}, generator=FakeGenerator()).build_report(
            quality_report
        )

        headline_task = next(task for task in report.tasks if task.task_type == "headline")
        self.assertTrue(any(option.source == "llm" for option in headline_task.options))
        self.assertTrue(
            any(option.content == "城市更新跑出新速度" for option in headline_task.options)
        )
        self.assertFalse(
            any("震惊" in option.content for option in headline_task.options)
        )

    def test_phase4_evaluation_runner_reports_pass_rates(self):
        root_dir = Path(__file__).resolve().parents[1]
        report = evaluate_case_files(
            root_dir=root_dir,
            safety_cases_path=root_dir / "tests" / "fixtures" / "safety_eval_cases.json",
            optimization_cases_path=root_dir
            / "tests"
            / "fixtures"
            / "optimization_eval_cases.json",
        )

        self.assertIn("summary", report)
        self.assertIn("safety_pass_rate", report["summary"])
        self.assertGreaterEqual(report["summary"]["overall_pass_rate"], 0.0)
        self.assertEqual(len(report["safety_results"]), 2)
        self.assertEqual(len(report["optimization_results"]), 2)


if __name__ == "__main__":
    unittest.main()
