"""
Shared audit pipeline for the intelligent editor CLIs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from parser_auditor import AnomalyDetector, HeuristicsChecker, MetricsCalculator

from intelligent_editor.core.decision_engine import DecisionEngine
from intelligent_editor.core.explanation_engine import ExplanationEngine
from intelligent_editor.core.optimization_engine import OptimizationEngine
from intelligent_editor.core.risk_engine import RiskEngine
from intelligent_editor.core.scoring_engine import ScoringEngine
from intelligent_editor.core.top_issues_extractor import TopIssuesExtractor
from intelligent_editor.utils.config_loader import ConfigLoader

logger = logging.getLogger("intelligent_editor")


@dataclass
class BaseAuditArtifacts:
    data: Dict[str, Any]
    metrics: Dict[str, Any]
    issues: list
    anomalies: Dict[str, Any]
    configs: Dict[str, Dict[str, Any]]
    risks: list
    score: Any
    decision: Any
    top_issues: list
    explanation: Any
    optimization_report: Any


def load_structured_data(json_path: str) -> Dict[str, Any]:
    """Load structured parser output from disk."""
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        logger.error("File not found: %s", json_path)
        raise FileNotFoundError(f"无法找到文件: {json_path}") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON file %s: %s", json_path, exc)
        raise ValueError(f"JSON格式无效: {exc}") from exc


def load_configs_and_validate_strategy(strategy: str) -> Dict[str, Dict[str, Any]]:
    """Load all configs and ensure the selected strategy exists."""
    configs = ConfigLoader.load_all_configs()
    valid_strategies = configs.get("decision", {}).get("strategies", {}).keys()
    if strategy not in valid_strategies:
        raise ValueError(
            f"无效的策略名称 '{strategy}'. 有效策略: {', '.join(valid_strategies)}"
        )
    return configs


def run_base_audit(json_path: str, strategy: str = "balanced") -> BaseAuditArtifacts:
    """Run the publication audit pipeline shared by v1 and v2 CLIs."""
    logger.info("Starting shared audit pipeline for %s", json_path)

    data = load_structured_data(json_path)

    logger.info("Running parser_auditor metrics and checks...")
    metrics = MetricsCalculator(data).calculate_all_metrics()
    issues = HeuristicsChecker(data).check_all()
    anomalies = AnomalyDetector(data).detect_all()
    logger.info(
        "Found %s issues and %s anomalies",
        len(issues),
        sum(len(items) for items in anomalies.values()),
    )

    logger.info("Loading intelligent_editor configs...")
    configs = load_configs_and_validate_strategy(strategy)

    risk_engine = RiskEngine(configs["risk"])
    decision_engine = DecisionEngine(configs["decision"])
    scoring_engine = ScoringEngine(configs["scoring"])
    explanation_engine = ExplanationEngine(configs.get("explanation", {}))
    top_issues_extractor = TopIssuesExtractor(configs.get("top_issues", {}))
    optimization_engine = OptimizationEngine(configs.get("optimization", {}))

    logger.info("Identifying risks...")
    risks = risk_engine.identify_risks(issues, anomalies, metrics)

    logger.info("Calculating publication score...")
    score = scoring_engine.calculate_score(risks, metrics)

    logger.info("Making publication decision...")
    decision = decision_engine.make_decision(risks, metrics, strategy)

    logger.info("Extracting top issues...")
    top_issues = top_issues_extractor.extract_top_issues(risks, decision)

    logger.info("Generating explanations and optimization suggestions...")
    explanation = explanation_engine.generate_explanation(
        decision, score, top_issues, risks
    )
    optimization_report = optimization_engine.generate_suggestions(data, metrics, risks)

    return BaseAuditArtifacts(
        data=data,
        metrics=metrics,
        issues=issues,
        anomalies=anomalies,
        configs=configs,
        risks=risks,
        score=score,
        decision=decision,
        top_issues=top_issues,
        explanation=explanation,
        optimization_report=optimization_report,
    )


def ensure_output_dir(output_dir: str) -> Path:
    """Create the output directory if it does not already exist."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def decision_to_exit_code(decision: str) -> int:
    """Translate a decision string into the CLI exit code convention."""
    normalized = decision.lower()
    if normalized == "approve":
        return 0
    if normalized == "review":
        return 1
    if normalized == "reject":
        return 2
    return 3
