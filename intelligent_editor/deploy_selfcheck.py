"""
Deployment self-check for the intelligent editor server environment.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from intelligent_editor.main_v2 import audit_layout_v2
from intelligent_editor.utils.config_loader import ConfigLoader


def run_check(name: str, passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def get_git_head(root_dir: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_git_status(root_dir: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=root_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def perform_selfcheck(root_dir: Path, sample_json: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    configs = ConfigLoader.load_all_configs()
    current_commit = get_git_head(root_dir)
    git_status = get_git_status(root_dir)

    checks.append(
        run_check(
            "python_available",
            True,
            f"Python {sys.version.split()[0]}",
        )
    )
    checks.append(
        run_check(
            "git_head_present",
            bool(current_commit),
            current_commit or "Unable to read git HEAD",
        )
    )
    checks.append(
        run_check(
            "git_worktree_clean",
            not bool(git_status),
            git_status or "Working tree is clean",
        )
    )
    checks.append(
        run_check(
            "sample_json_exists",
            sample_json.exists(),
            str(sample_json),
        )
    )

    required_configs = [
        "editorial_quality",
        "safety_evaluation",
        "optimization_generation",
    ]
    for config_name in required_configs:
        checks.append(
            run_check(
                f"config_loaded_{config_name}",
                config_name in configs,
                f"Loaded={config_name in configs}",
            )
        )

    env_checks = []
    for section_name in ("safety_evaluation", "optimization_generation"):
        section = configs.get(section_name, {}).get(section_name, {})
        env_name = section.get("api_key_env", "ARK_API_KEY")
        enabled = bool(section.get("enabled", False))
        env_present = bool(os.getenv(env_name))
        env_checks.append((section_name, env_name, enabled, env_present))
        checks.append(
            run_check(
                f"{section_name}_env_ready",
                (not enabled) or env_present,
                f"enabled={enabled}, env={env_name}, present={env_present}",
            )
        )

    rewrite_config = (
        configs.get("editorial_quality", {})
        .get("headline_rewrite", {})
        .get("llm_config", {})
    )
    rewrite_env = rewrite_config.get("api_key_env", "ARK_API_KEY")
    rewrite_enabled = bool(rewrite_config.get("enabled", False))
    rewrite_env_present = bool(os.getenv(rewrite_env))
    checks.append(
        run_check(
            "headline_rewrite_env_ready",
            (not rewrite_enabled) or rewrite_env_present,
            f"enabled={rewrite_enabled}, env={rewrite_env}, present={rewrite_env_present}",
        )
    )

    smoke_outputs = []
    smoke_ok = False
    smoke_detail = "Sample JSON missing"
    if sample_json.exists():
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                audit_layout_v2(str(sample_json), output_dir=temp_dir)
                expected = [
                    "intelligent_audit_report_v2.json",
                    "executive_audit_report.json",
                    "safety_report.md",
                    "optimization_report.md",
                ]
                smoke_outputs = [
                    name for name in expected if (Path(temp_dir) / name).exists()
                ]
                smoke_ok = len(smoke_outputs) == len(expected)
                smoke_detail = f"generated={', '.join(smoke_outputs)}"
        except Exception as exc:
            smoke_detail = str(exc)

    checks.append(run_check("main_v2_smoke", smoke_ok, smoke_detail))

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "root_dir": str(root_dir),
        "current_commit": current_commit,
        "sample_json": str(sample_json),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="服务器部署自检")
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="项目根目录",
    )
    parser.add_argument(
        "--sample-json",
        default="output/json/page_1_structured.json",
        help="用于冒烟测试的 structured.json",
    )
    parser.add_argument(
        "--output",
        default="deploy_selfcheck_report.json",
        help="自检报告输出文件",
    )
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    sample_json = (root_dir / args.sample_json).resolve()
    result = perform_selfcheck(root_dir, sample_json)
    output_path = root_dir / args.output
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n自检报告已写入: {output_path}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
