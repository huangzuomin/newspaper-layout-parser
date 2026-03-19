"""
Config loader utilities for YAML-based intelligent editor settings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger("intelligent_editor")


class ConfigLoader:
    """Load YAML config files from the intelligent_editor config directory."""

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Load one YAML config file from an explicit or module-relative path."""
        config_file = Path(config_path)

        if not config_file.exists():
            module_dir = Path(__file__).parent.parent
            config_file = module_dir / "config" / config_path
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_file, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
            logger.debug("Loaded config from %s", config_file)
            return config
        except yaml.YAMLError as exc:
            logger.error("Invalid YAML in %s: %s", config_file, exc)
            raise

    @staticmethod
    def load_all_configs(config_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Load all known config files under the module config directory."""
        if config_dir is None:
            config_root = Path(__file__).parent.parent / "config"
        else:
            config_root = Path(config_dir)

        configs: Dict[str, Dict[str, Any]] = {}
        file_map = {
            "risk": "risk_rules.yaml",
            "decision": "decision_strategy.yaml",
            "scoring": "scoring_weights.yaml",
            "top_issues": "top_issues_config.yaml",
            "editorial_quality": "editorial_quality.yaml",
            "safety_evaluation": "safety_evaluation.yaml",
            "optimization_generation": "optimization_generation.yaml",
            "explanation": "explanation_templates.yaml",
            "optimization": "optimization_rules.yaml",
        }

        for key, filename in file_map.items():
            config_file = config_root / filename
            if not config_file.exists():
                if key in {"risk", "decision"}:
                    logger.warning("Required config not found: %s", config_file)
                continue

            with open(config_file, "r", encoding="utf-8") as file:
                configs[key] = yaml.safe_load(file) or {}
            logger.debug("Loaded %s config from %s", key, config_file)

        return configs

    @staticmethod
    def get_strategy_config(
        decision_config: Dict[str, Any], strategy_name: str = "balanced"
    ) -> Dict[str, Any]:
        """Return the selected decision strategy or the configured default."""
        strategies = decision_config.get("strategies", {})

        if strategy_name not in strategies:
            default_strategy = decision_config.get("default_strategy", "balanced")
            logger.warning(
                "Strategy '%s' not found, using default '%s'",
                strategy_name,
                default_strategy,
            )
            strategy_name = default_strategy

        return strategies[strategy_name]
