"""
字体分析器（频次统计为主，KMeans为辅）
Font Analyzer - Frequency-based font hierarchy detection
"""

import numpy as np
from sklearn.cluster import KMeans
from typing import List, Dict, Tuple, Any
from collections import Counter
import logging

from .schema import Block

logger = logging.getLogger("parser")


class FontAnalyzer:
    """字体层级分析器"""

    def __init__(self):
        """初始化字体分析器"""
        # 默认阈值配置
        self.headline_to_body_ratio = 1.4
        self.subheadline_to_body_ratio = 1.15
        self.caption_to_body_ratio = 0.85

        # 峰值检测参数
        self.peak_window_size = 1.0  # 峰值检测窗口（pt）
        self.min_peak_confidence = 0.7

    def analyze(self, blocks: List[Block]) -> Dict[str, Any]:
        """
        分析字体层级

        Args:
            blocks: Block列表

        Returns:
            字体配置字典
        """
        logger.info("Analyzing font hierarchy...")

        # 收集所有字体大小和权重
        font_sizes = []
        font_weights = []

        for block in blocks:
            if block.char_count > 0 and block.font_sizes:
                # 使用主字体
                font_sizes.append(block.font_size)
                font_weights.append(block.font_weight)

        if not font_sizes:
            logger.warning("No valid font sizes found, using default profile")
            return self._default_profile()

        # 方法1：频次分析（主策略）
        profile = self._frequency_analysis(font_sizes, font_weights)

        # 如果频次分析失败，使用KMeans兜底
        if profile["method"] == "frequency_fallback":
            logger.warning("Frequency analysis failed, trying KMeans fallback")
            profile = self._kmeans_analysis(font_sizes)

        logger.info(f"Font profile (method={profile['method']}):")
        for font_type, value in profile.items():
            if font_type not in ["method", "body_peak", "peak_confidence"] and isinstance(value, tuple) and len(value) == 3:
                min_size, max_size, avg_size = value
                logger.info(f"  {font_type}: {min_size:.2f}-{max_size:.2f}pt (avg: {avg_size:.2f}pt)")

        return profile

    def _frequency_analysis(
        self, font_sizes: List[float], font_weights: List[float]
    ) -> Dict[str, Any]:
        """
        基于频次统计的字体分析（主策略）

        Args:
            font_sizes: 字体大小列表
            font_weights: 字体权重（字符数）列表

        Returns:
            字体配置字典
        """
        # 1. 按字符数加权统计字体大小频次
        weighted_font_counts = Counter()
        for size, weight in zip(font_sizes, font_weights):
            # 将字体大小舍入到0.5pt精度
            rounded_size = round(size * 2) / 2
            weighted_font_counts[rounded_size] += weight

        if not weighted_font_counts:
            return self._default_profile()

        # 2. 找到主峰（频次最高的字体大小）
        peak_size, peak_weight = weighted_font_counts.most_common(1)[0]
        total_weight = sum(weighted_font_counts.values())
        peak_confidence = peak_weight / total_weight

        logger.debug(f"Font peak: {peak_size}pt (confidence: {peak_confidence:.2%})")

        # 3. 验证主峰（检查是否有明显的第二峰）
        if peak_confidence < self.min_peak_confidence:
            logger.warning(
                f"Peak confidence too low ({peak_confidence:.2%}), using KMeans"
            )
            return {"method": "frequency_fallback"}

        # 4. 检查峰的合理性（应该在8-20pt范围内）
        if not (8 <= peak_size <= 20):
            logger.warning(f"Peak size {peak_size}pt out of reasonable range, using KMeans")
            return {"method": "frequency_fallback"}

        # 5. 推导其他层级
        body_peak = peak_size

        # 计算阈值
        headline_min = body_peak * self.headline_to_body_ratio
        subheadline_min = body_peak * self.subheadline_to_body_ratio
        caption_max = body_peak * self.caption_to_body_ratio

        # 估算各级字体范围
        # headline: body * 1.4 ~ body * 2.0
        # subheadline: body * 1.15 ~ body * 1.4
        # body: body * 0.9 ~ body * 1.15
        # caption: body * 0.7 ~ body * 0.9

        profile = {
            "headline": (
                headline_min,
                body_peak * 2.0,
                (headline_min + body_peak * 2.0) / 2,
            ),
            "subheadline": (
                subheadline_min,
                body_peak * 1.4,
                (subheadline_min + body_peak * 1.4) / 2,
            ),
            "body": (
                body_peak * 0.9,
                body_peak * 1.15,
                body_peak,
            ),
            "caption": (
                body_peak * 0.7,
                caption_max,
                (body_peak * 0.7 + caption_max) / 2,
            ),
            "method": "frequency",
            "body_peak": body_peak,
            "peak_confidence": peak_confidence,
        }

        return profile

    def _kmeans_analysis(self, font_sizes: List[float]) -> Dict[str, Any]:
        """
        基于KMeans的字体分析（兜底策略）

        Args:
            font_sizes: 字体大小列表

        Returns:
            字体配置字典
        """
        logger.info("Using KMeans clustering for font analysis")

        # 转换为numpy数组
        sizes_array = np.array(font_sizes).reshape(-1, 1)

        # 估计聚类数
        unique_sizes = len(set(font_sizes))
        n_clusters = min(4, unique_sizes)

        if n_clusters < 2:
            logger.warning("Not enough unique font sizes, using default profile")
            return self._default_profile()

        # KMeans聚类
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(sizes_array)
        except Exception as e:
            logger.error(f"KMeans failed: {e}, using default profile")
            return self._default_profile()

        # 分析每个簇
        clusters = {}
        for i in range(n_clusters):
            cluster_sizes = sizes_array[labels == i].flatten()
            clusters[i] = {
                "sizes": cluster_sizes.tolist(),
                "mean": float(np.mean(cluster_sizes)),
                "min": float(np.min(cluster_sizes)),
                "max": float(np.max(cluster_sizes)),
                "count": len(cluster_sizes),
            }

        # 按平均大小排序
        sorted_clusters = sorted(clusters.items(), key=lambda x: x[1]["mean"], reverse=True)

        # 映射到字体类型
        profile = {"method": "kmeans_fallback"}

        if len(sorted_clusters) >= 4:
            # 4个层级
            for i, (cluster_id, cluster_info) in enumerate(sorted_clusters):
                if i == 0:
                    font_type = "headline"
                elif i == 1:
                    font_type = "subheadline"
                elif i == 2:
                    font_type = "body"
                else:
                    font_type = "caption"

                profile[font_type] = (
                    cluster_info["min"],
                    cluster_info["max"],
                    cluster_info["mean"],
                )
        elif len(sorted_clusters) == 3:
            # 3个层级
            profile["headline"] = self._make_range(sorted_clusters[0][1])
            profile["body"] = self._make_range(sorted_clusters[1][1])
            profile["caption"] = self._make_range(sorted_clusters[2][1])
        elif len(sorted_clusters) == 2:
            # 2个层级
            profile["headline"] = self._make_range(sorted_clusters[0][1])
            profile["body"] = self._make_range(sorted_clusters[1][1])
            # caption使用body的较小值
            body_min = sorted_clusters[1][1]["min"]
            profile["caption"] = (body_min * 0.7, body_min * 0.9, body_min * 0.8)
        else:
            # 只有1个层级
            profile["body"] = self._make_range(sorted_clusters[0][1])

        return profile

    def _make_range(self, cluster_info: Dict) -> Tuple[float, float, float]:
        """
        创建字体范围（min, max, avg）

        Args:
            cluster_info: 簇信息

        Returns:
            (min_size, max_size, avg_size)
        """
        mean = cluster_info["mean"]
        # 添加20%的容差
        margin = mean * 0.2
        return (max(0, cluster_info["min"] - margin), cluster_info["max"] + margin, mean)

    def _default_profile(self) -> Dict[str, Any]:
        """默认字体配置"""
        return {
            "headline": (18.0, 36.0, 24.0),
            "subheadline": (14.0, 18.0, 16.0),
            "body": (9.0, 13.0, 11.0),
            "caption": (7.0, 9.0, 8.0),
            "method": "default",
        }

    def get_font_type(
        self, font_size: float, profile: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        根据字体大小判断类型

        Args:
            font_size: 字体大小
            profile: 字体配置

        Returns:
            (font_type, confidence)
        """
        for font_type in ["headline", "subheadline", "body", "caption"]:
            if font_type in profile:
                min_size, max_size, avg_size = profile[font_type]
                if min_size <= font_size <= max_size:
                    # 计算置信度（越接近平均值越可信）
                    distance = abs(font_size - avg_size)
                    confidence = max(0, 1 - distance / (max_size - min_size))
                    return font_type, confidence

        # 默认为body
        if "body" in profile:
            _, _, avg_size = profile["body"]
            return "body", 0.5

        return "body", 0.5
