import json
import tempfile
import unittest
from pathlib import Path

from intelligent_editor.main import audit_layout
from intelligent_editor.main_v2 import audit_layout_v2


ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_JSON = ROOT_DIR / "output" / "json" / "page_1_structured.json"
SECOND_SAMPLE_JSON = ROOT_DIR / "output" / "json" / "example_result.json"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class EndToEndReportTests(unittest.TestCase):
    def test_publication_report_matches_golden_summary(self):
        expected = load_fixture("golden_publication_summary.json")

        with tempfile.TemporaryDirectory() as temp_dir:
            report = audit_layout(str(SAMPLE_JSON), output_dir=temp_dir)
            summary = {
                "decision": report["level1_decision"]["decision"],
                "risk_level": report["level1_decision"]["risk_level"],
                "score": report["level2_score"]["score"],
                "grade": report["level2_score"]["grade"],
                "top_issue_count": len(report["level3_top_issues"]),
                "optimization_count": report["level6_optimization"]["total_count"],
            }

            self.assertEqual(summary, expected)
            self.assertEqual(
                report["level3_top_issues"][0]["summary"],
                "文章 a_right_zone_noheadline 缺少标题",
            )
            self.assertEqual(
                report["level3_top_issues"][0]["action_needed"],
                "补齐标题并复核文章归类",
            )
            self.assertTrue((Path(temp_dir) / "intelligent_audit_report.json").exists())
            self.assertTrue((Path(temp_dir) / "audit_summary.txt").exists())
            self.assertTrue((Path(temp_dir) / "editor_report.txt").exists())

    def test_publication_report_second_sample_matches_golden_shape(self):
        expected = load_fixture("golden_publication_summary.json")

        with tempfile.TemporaryDirectory() as temp_dir:
            report = audit_layout(str(SECOND_SAMPLE_JSON), output_dir=temp_dir)
            summary = {
                "decision": report["level1_decision"]["decision"],
                "risk_level": report["level1_decision"]["risk_level"],
                "score": report["level2_score"]["score"],
                "grade": report["level2_score"]["grade"],
                "top_issue_count": len(report["level3_top_issues"]),
                "optimization_count": report["level6_optimization"]["total_count"],
            }

            self.assertEqual(summary, expected)
            self.assertTrue((Path(temp_dir) / "intelligent_audit_report.json").exists())

    def test_dual_channel_report_matches_golden_summary(self):
        expected = load_fixture("golden_dual_channel_summary.json")

        with tempfile.TemporaryDirectory() as temp_dir:
            report = audit_layout_v2(str(SAMPLE_JSON), output_dir=temp_dir)
            summary = {
                "decision": report.publication_decision.decision,
                "risk_level": report.publication_decision.risk_level,
                "overall_score": round(
                    report.quality_improvement.assessment.overall_score, 1
                ),
                "overall_grade": report.quality_improvement.assessment.overall_grade,
                "total_suggestions": report.quality_improvement.total_suggestions,
                "top_improvement_count": len(
                    report.quality_improvement.top_improvement_points
                ),
            }

            self.assertEqual(summary, expected)
            self.assertEqual(
                report.publication_decision.blocking_issues[0],
                "文章 a_right_zone_noheadline 缺少标题",
            )

            editor_report = (Path(temp_dir) / "editor_report_v2.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("当前阻断项", editor_report)
            self.assertIn("导语核心信息前置不足", editor_report)
            self.assertIn("涉及5篇稿件", editor_report)

            executive_report = json.loads(
                (Path(temp_dir) / "executive_audit_report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                executive_report["executive_summary"]["manual_review_required"], True
            )
            self.assertEqual(
                executive_report["safety_report"]["semantic_review_enabled"], False
            )
            self.assertEqual(
                executive_report["engineering_baseline"][
                    "finding_count"
                ],
                len(executive_report["engineering_baseline"]["findings"]),
            )

            safety_report = (Path(temp_dir) / "safety_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("总编辑安全报告", safety_report)
            self.assertIn("人工复核", safety_report)

            optimization_report = (Path(temp_dir) / "optimization_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("总编辑优化报告", optimization_report)
            self.assertIn("Top 编辑任务", optimization_report)
            self.assertIn("底线附录", optimization_report)

            self.assertTrue(
                (Path(temp_dir) / "intelligent_audit_report_v2.json").exists()
            )
            self.assertTrue((Path(temp_dir) / "editor_report_v2.txt").exists())
            self.assertTrue((Path(temp_dir) / "improvement_suggestions.md").exists())
            self.assertTrue((Path(temp_dir) / "executive_audit_report.json").exists())
            self.assertTrue((Path(temp_dir) / "safety_report.md").exists())
            self.assertTrue((Path(temp_dir) / "optimization_report.md").exists())

    def test_dual_channel_report_second_sample_matches_golden_summary(self):
        expected = load_fixture("golden_dual_channel_summary.json")

        with tempfile.TemporaryDirectory() as temp_dir:
            report = audit_layout_v2(str(SECOND_SAMPLE_JSON), output_dir=temp_dir)
            summary = {
                "decision": report.publication_decision.decision,
                "risk_level": report.publication_decision.risk_level,
                "overall_score": round(
                    report.quality_improvement.assessment.overall_score, 1
                ),
                "overall_grade": report.quality_improvement.assessment.overall_grade,
                "total_suggestions": report.quality_improvement.total_suggestions,
                "top_improvement_count": len(
                    report.quality_improvement.top_improvement_points
                ),
            }

            self.assertEqual(summary, expected)
            self.assertTrue(
                (Path(temp_dir) / "intelligent_audit_report_v2.json").exists()
            )
            self.assertTrue((Path(temp_dir) / "executive_audit_report.json").exists())


if __name__ == "__main__":
    unittest.main()
