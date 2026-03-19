"""
CLI for Phase 4 report evaluation and calibration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from intelligent_editor.evaluation import evaluate_case_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 4 评测脚本：校验安全报告与优化报告的样例通过率"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="项目根目录，默认使用当前仓库根目录",
    )
    parser.add_argument(
        "--safety-cases",
        default="tests/fixtures/safety_eval_cases.json",
        help="安全评估样例路径",
    )
    parser.add_argument(
        "--optimization-cases",
        default="tests/fixtures/optimization_eval_cases.json",
        help="优化评估样例路径",
    )
    parser.add_argument(
        "--output",
        default="phase4_evaluation_report.json",
        help="评测结果输出文件",
    )
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    result = evaluate_case_files(
        root_dir=root_dir,
        safety_cases_path=root_dir / args.safety_cases,
        optimization_cases_path=root_dir / args.optimization_cases,
    )

    output_path = root_dir / args.output
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"\n评测结果已写入: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
