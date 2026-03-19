"""
Phase 4 evaluation helpers for safety and optimization reports.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from intelligent_editor.main_v2 import audit_layout_v2


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_executive_report(input_json: Path) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_layout_v2(str(input_json), output_dir=temp_dir)
        report_path = Path(temp_dir) / "executive_audit_report.json"
        return load_json(report_path)


def evaluate_safety_case(report: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
    safety = report["safety_report"]
    checks: List[Dict[str, Any]] = []

    checks.append(
        _check(
            "recommendation_match",
            safety["recommendation"] == case["expected_recommendation"],
        )
    )
    checks.append(
        _check("risk_level_match", safety["risk_level"] == case["expected_risk_level"])
    )
    checks.append(
        _check(
            "manual_review_match",
            safety["requires_manual_review"] == case["requires_manual_review"],
        )
    )
    checks.append(
        _check(
            "minimum_findings",
            len(safety.get("findings", [])) >= case["minimum_findings"],
        )
    )

    report_text = json.dumps(safety, ensure_ascii=False)
    for index, group in enumerate(case.get("expected_keyword_groups", []), start=1):
        checks.append(
            _check(
                f"keyword_group_{index}",
                any(keyword in report_text for keyword in group),
            )
        )

    return _case_result(case["id"], "safety", checks)


def evaluate_optimization_case(
    report: Dict[str, Any], case: Dict[str, Any]
) -> Dict[str, Any]:
    optimization = report["optimization_report"]
    tasks = optimization.get("tasks", [])
    checks: List[Dict[str, Any]] = []

    checks.append(
        _check("minimum_task_count", len(tasks) >= case["minimum_task_count"])
    )

    task_map = {item["task_type"]: item for item in tasks}
    for task_type in case.get("expected_task_types", []):
        checks.append(_check(f"task_present_{task_type}", task_type in task_map))
        if task_type in task_map:
            minimum_options = case.get("minimum_options_per_task", {}).get(task_type, 1)
            checks.append(
                _check(
                    f"option_count_{task_type}",
                    len(task_map[task_type].get("options", [])) >= minimum_options,
                )
            )

    return _case_result(case["id"], "optimization", checks)


def evaluate_case_files(
    root_dir: Path,
    safety_cases_path: Path,
    optimization_cases_path: Path,
) -> Dict[str, Any]:
    safety_cases = load_json(safety_cases_path)
    optimization_cases = load_json(optimization_cases_path)
    report_cache: Dict[str, Dict[str, Any]] = {}

    safety_results = []
    for case in safety_cases:
        report = _load_or_run_case_report(root_dir, report_cache, case["input_json"])
        safety_results.append(evaluate_safety_case(report, case))

    optimization_results = []
    for case in optimization_cases:
        report = _load_or_run_case_report(root_dir, report_cache, case["input_json"])
        optimization_results.append(evaluate_optimization_case(report, case))

    return {
        "summary": {
            "safety_pass_rate": _pass_rate(safety_results),
            "optimization_pass_rate": _pass_rate(optimization_results),
            "overall_pass_rate": _pass_rate(safety_results + optimization_results),
        },
        "safety_results": safety_results,
        "optimization_results": optimization_results,
    }


def _load_or_run_case_report(
    root_dir: Path, report_cache: Dict[str, Dict[str, Any]], relative_path: str
) -> Dict[str, Any]:
    if relative_path not in report_cache:
        report_cache[relative_path] = run_executive_report(root_dir / relative_path)
    return report_cache[relative_path]


def _check(name: str, passed: bool) -> Dict[str, Any]:
    return {"name": name, "passed": passed}


def _case_result(case_id: str, case_type: str, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    passed = all(item["passed"] for item in checks)
    return {
        "id": case_id,
        "type": case_type,
        "passed": passed,
        "checks": checks,
    }


def _pass_rate(results: List[Dict[str, Any]]) -> float:
    if not results:
        return 0.0
    passed = sum(1 for item in results if item["passed"])
    return round(passed / len(results), 3)
