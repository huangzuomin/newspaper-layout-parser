"""
配置加载器
Config Loader
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("intelligent_editor")


class ConfigLoader:
    """配置加载器 - 加载YAML配置文件"""

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        加载单个YAML配置文件

        Args:
            config_path: 配置文件路径（相对或绝对）

        Returns:
            配置字典
        """
        config_file = Path(config_path)

        if not config_file.exists():
            # 尝试从模块目录加载
            module_dir = Path(__file__).parent.parent
            config_file = module_dir / "config" / config_path

            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            logger.debug(f"Loaded config from {config_file}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {config_file}: {e}")
            raise

    @staticmethod
    def load_all_configs(config_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        加载所有配置文件

        Args:
            config_dir: 配置目录路径（默认为intelligent_editor/config）

        Returns:
            包含所有配置的字典
        """
        if config_dir is None:
            # 默认使用模块的config目录
            module_dir = Path(__file__).parent.parent
            config_dir = module_dir / "config"
        else:
            config_dir = Path(config_dir)

        configs = {}

        # 加载risk_rules.yaml
        risk_config_file = config_dir / "risk_rules.yaml"
        if risk_config_file.exists():
            with open(risk_config_file, 'r', encoding='utf-8') as f:
                configs['risk'] = yaml.safe_load(f)
            logger.debug(f"Loaded risk config from {risk_config_file}")
        else:
            logger.warning(f"Risk config not found: {risk_config_file}")

        # 加载decision_strategy.yaml
        decision_config_file = config_dir / "decision_strategy.yaml"
        if decision_config_file.exists():
            with open(decision_config_file, 'r', encoding='utf-8') as f:
                configs['decision'] = yaml.safe_load(f)
            logger.debug(f"Loaded decision config from {decision_config_file}")
        else:
            logger.warning(f"Decision config not found: {decision_config_file}")

        # 加载scoring_weights.yaml（Phase 2）
        scoring_config_file = config_dir / "scoring_weights.yaml"
        if scoring_config_file.exists():
            with open(scoring_config_file, 'r', encoding='utf-8') as f:
                configs['scoring'] = yaml.safe_load(f)
            logger.debug(f"Loaded scoring config from {scoring_config_file}")

        # 加载top_issues_config.yaml
        top_issues_config_file = config_dir / "top_issues_config.yaml"
        if top_issues_config_file.exists():
            with open(top_issues_config_file, 'r', encoding='utf-8') as f:
                configs['top_issues'] = yaml.safe_load(f)
            logger.debug(f"Loaded top_issues config from {top_issues_config_file}")

        return configs

    @staticmethod
    def get_strategy_config(
        decision_config: Dict[str, Any],
        strategy_name: str = 'balanced'
    ) -> Dict[str, Any]:
        """
        获取指定策略的配置

        Args:
            decision_config: 决策配置字典
            strategy_name: 策略名称（conservative/balanced/aggressive）

        Returns:
            策略配置字典
        """
        strategies = decision_config.get('strategies', {})

        if strategy_name not in strategies:
            default_strategy = decision_config.get('default_strategy', 'balanced')
            logger.warning(f"Strategy '{strategy_name}' not found, using default '{default_strategy}'")
            strategy_name = default_strategy

        return strategies[strategy_name]
