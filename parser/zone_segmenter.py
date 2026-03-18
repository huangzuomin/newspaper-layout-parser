"""
区域分区器（配置驱动）
Zone Segmenter - Divide page into zones using configuration
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
import logging

from .schema import Block, ZoneType, BBox

logger = logging.getLogger("parser")


class ZoneSegmenter:
    """区域分区器"""

    def __init__(self, profile_path: str = None, profile_name: str = "default"):
        """
        初始化区域分区器

        Args:
            profile_path: 配置文件路径（默认为parser/config/layout_profile.yaml）
            profile_name: 使用的配置名称（default/front_page/financial_page等）
        """
        if profile_path is None:
            profile_path = Path(__file__).parent / "config" / "layout_profile.yaml"

        self.profile_path = Path(profile_path)
        self.profile_name = profile_name
        self.config = self._load_config()
        self.profile = self.config.get("profiles", {}).get(profile_name, {})

        if not self.profile:
            logger.warning(f"Profile '{profile_name}' not found, using default zones")
            self.profile = self._get_default_profile()

        logger.debug(f"Loaded zone profile: {profile_name}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.profile_path.exists():
            logger.warning(f"Config file not found: {self.profile_path}, using defaults")
            return {"profiles": {"default": self._get_default_profile()}}

        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.debug(f"Loaded config from: {self.profile_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return {"profiles": {"default": self._get_default_profile()}}

    def _get_default_profile(self) -> Dict[str, Any]:
        """获取默认区域配置"""
        return {
            "zones": {
                "masthead": {"y_max_ratio": 0.15, "priority": 0},
                "headline_zone": {"y_min_ratio": 0.15, "y_max_ratio": 0.30, "priority": 1},
                "left_zone": {"y_min_ratio": 0.30, "y_max_ratio": 0.75, "x_max_ratio": 0.65, "priority": 2},
                "right_zone": {"y_min_ratio": 0.30, "y_max_ratio": 0.75, "x_min_ratio": 0.65, "priority": 3},
                "bottom_zone": {"y_min_ratio": 0.75, "priority": 4},
            }
        }

    def segment(
        self, blocks: List[Block], page_width: float, page_height: float
    ) -> List[Block]:
        """
        为每个block分配区域

        Args:
            blocks: Block列表
            page_width: 页面宽度
            page_height: 页面高度

        Returns:
            更新了zone信息的Block列表
        """
        logger.debug(f"Segmenting {len(blocks)} blocks into zones")

        # 统计各zone的blocks数量
        zone_counts = {}

        for block in blocks:
            zone = self._get_zone(block.bbox, page_width, page_height)
            block.zone = zone

            zone_counts[zone.value] = zone_counts.get(zone.value, 0) + 1

        logger.info(f"Zone segmentation: {zone_counts}")
        return blocks

    def _get_zone(
        self, bbox: BBox, page_width: float, page_height: float
    ) -> ZoneType:
        """
        根据bbox判断所属区域

        Args:
            bbox: 边界框
            page_width: 页面宽度
            page_height: 页面高度

        Returns:
            ZoneType枚举值
        """
        # 计算中心点
        center_x, center_y = bbox.center

        # 归一化坐标（0-1）
        norm_x = center_x / page_width
        norm_y = center_y / page_height

        # 按priority顺序检查zones
        zones = self.profile.get("zones", {})

        # 按priority排序
        sorted_zones = sorted(
            zones.items(),
            key=lambda x: x[1].get("priority", 999)
        )

        for zone_name, zone_config in sorted_zones:
            if self._in_zone(norm_x, norm_y, zone_config):
                try:
                    return ZoneType(zone_name)
                except ValueError:
                    logger.warning(f"Unknown zone type: {zone_name}")
                    continue

        # 默认返回left_zone
        return ZoneType.LEFT_ZONE

    def _in_zone(self, norm_x: float, norm_y: float, zone_config: Dict) -> bool:
        """
        判断归一化坐标是否在区域内

        Args:
            norm_x: 归一化x坐标（0-1）
            norm_y: 归一化y坐标（0-1）
            zone_config: 区域配置

        Returns:
            是否在区域内
        """
        # y方向约束
        y_min = zone_config.get("y_min_ratio", 0.0)
        y_max = zone_config.get("y_max_ratio", 1.0)

        if not (y_min <= norm_y <= y_max):
            return False

        # x方向约束（可选）
        x_min = zone_config.get("x_min_ratio", 0.0)
        x_max = zone_config.get("x_max_ratio", 1.0)

        if not (x_min <= norm_x <= x_max):
            return False

        return True
