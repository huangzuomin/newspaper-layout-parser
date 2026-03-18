"""
分栏检测器（Gap-based为主，KMeans为辅）
Column Detector - Detect column structure using gap analysis
"""

import numpy as np
from sklearn.cluster import KMeans
from typing import List, Tuple, Optional
import logging

from .schema import Block, BlockType

logger = logging.getLogger("parser")


class ColumnDetector:
    """分栏检测器"""

    def __init__(self):
        """初始化分栏检测器"""
        self.gap_threshold_multiplier = 2.0  # gap阈值倍数（提高以减少误判）
        self.min_column_width_ratio = 0.10  # 最小栏宽比例（相对于页面宽度）10%
        self.min_char_count = 30  # 参与分栏的最小字符数

    def detect(self, blocks: List[Block]) -> List[Block]:
        """
        检测栏结构（按zone分别分栏，使用全局column编号）

        Args:
            blocks: Block列表

        Returns:
            更新了column信息的Block列表
        """
        logger.info("Detecting column structure...")

        # 获取页面宽度（从第一个block）
        page_width = blocks[0].bbox.x1 if blocks else 965

        # 按zone分组进行分栏检测
        from .schema import ZoneType

        # 定义zones及其是否需要分栏
        zone_config = {
            ZoneType.LEFT_ZONE: {'detect': True, 'start_col': 0},
            ZoneType.RIGHT_ZONE: {'detect': False, 'start_col': None},  # 右侧主稿通常1栏
            ZoneType.HEADLINE_ZONE: {'detect': False, 'start_col': None},  # 通栏标题
            ZoneType.BOTTOM_ZONE: {'detect': True, 'start_col': None},  # 底部可能多栏
            ZoneType.MASTHEAD: {'detect': False, 'start_col': None},  # 报头不分栏
        }

        # 先为需要分栏的zones检测分栏，记录每个zone的栏数
        zone_column_counts = {}
        current_col = 0

        # 第一轮：left_zone分栏
        if ZoneType.LEFT_ZONE in [b.zone for b in blocks]:
            zone = ZoneType.LEFT_ZONE
            zone_blocks = [b for b in blocks if b.zone == zone]
            candidate_blocks = self._filter_column_candidates(zone_blocks)

            if len(candidate_blocks) >= 2:
                logger.debug(f"Zone {zone.value}: using {len(candidate_blocks)} candidate blocks")
                if self._try_gap_based_clustering(candidate_blocks, page_width):
                    self._assign_columns_to_zone(zone_blocks, candidate_blocks, base_col=current_col)
                    # 统计该zone实际栏数
                    cols_in_zone = len(set(b.column for b in zone_blocks if b.column is not None))
                    zone_column_counts[zone] = cols_in_zone
                    current_col += cols_in_zone
                else:
                    self._kmeans_clustering_zone(zone_blocks, page_width, base_col=current_col)
                    cols_in_zone = len(set(b.column for b in zone_blocks if b.column is not None))
                    zone_column_counts[zone] = cols_in_zone
                    current_col += cols_in_zone
            else:
                # 不够分栏，统一为1栏
                for block in zone_blocks:
                    block.column = current_col
                zone_column_counts[zone] = 1
                current_col += 1

        # right_zone：统一为1栏
        if ZoneType.RIGHT_ZONE in [b.zone for b in blocks]:
            for block in blocks:
                if block.zone == ZoneType.RIGHT_ZONE:
                    block.column = current_col
            zone_column_counts[ZoneType.RIGHT_ZONE] = 1
            current_col += 1

        # headline_zone：统一为1栏（通栏）
        if ZoneType.HEADLINE_ZONE in [b.zone for b in blocks]:
            for block in blocks:
                if block.zone == ZoneType.HEADLINE_ZONE:
                    block.column = current_col
            zone_column_counts[ZoneType.HEADLINE_ZONE] = 1
            current_col += 1

        # bottom_zone：分栏检测
        if ZoneType.BOTTOM_ZONE in [b.zone for b in blocks]:
            zone = ZoneType.BOTTOM_ZONE
            zone_blocks = [b for b in blocks if b.zone == zone]
            candidate_blocks = self._filter_column_candidates(zone_blocks)

            if len(candidate_blocks) >= 2:
                logger.debug(f"Zone {zone.value}: using {len(candidate_blocks)} candidate blocks")
                if self._try_gap_based_clustering(candidate_blocks, page_width):
                    self._assign_columns_to_zone(zone_blocks, candidate_blocks, base_col=current_col)
                    cols_in_zone = len(set(b.column for b in zone_blocks if b.column is not None))
                    zone_column_counts[zone] = cols_in_zone
                    current_col += cols_in_zone
                else:
                    self._kmeans_clustering_zone(zone_blocks, page_width, base_col=current_col)
                    cols_in_zone = len(set(b.column for b in zone_blocks if b.column is not None))
                    zone_column_counts[zone] = cols_in_zone
                    current_col += cols_in_zone
            else:
                for block in zone_blocks:
                    block.column = current_col
                zone_column_counts[zone] = 1
                current_col += 1

        # masthead：统一为column 0
        for block in blocks:
            if block.zone == ZoneType.MASTHEAD:
                block.column = 0

        logger.info(f"Column detection completed. Zone column counts: {zone_column_counts}")
        logger.info(f"Total columns: {current_col}")

        return blocks

    def _filter_column_candidates(self, blocks: List[Block]) -> List[Block]:
        """
        严格过滤：只允许真正的正文候选块参与分栏

        明确排除：
        - masthead区域的blocks
        - section_label类型的blocks
        - headline类型的blocks
        - 非常短的blocks（字符数<阈值）

        只允许：
        - body_candidate或subheadline_candidate
        - 字符数>=min_char_count
        - 不是被明确排除的类型

        Args:
            blocks: Block列表

        Returns:
            过滤后的候选Block列表
        """
        from .schema import ZoneType

        candidates = []
        excluded_count = 0

        for block in blocks:
            # 排除规则1: 明确的类型
            if block.type_candidate == BlockType.SECTION_LABEL:
                excluded_count += 1
                continue
            if block.type_candidate == BlockType.HEADLINE:
                excluded_count += 1
                continue
            if block.type_final == BlockType.SECTION_LABEL:
                excluded_count += 1
                continue
            if block.type_final == BlockType.HEADLINE:
                excluded_count += 1
                continue

            # 排除规则2: masthead区域的blocks
            if block.zone == ZoneType.MASTHEAD:
                excluded_count += 1
                continue

            # 排除规则3: 非常短的blocks
            if block.char_count < self.min_char_count:
                excluded_count += 1
                continue

            # 排除规则4: 图片
            if block.char_count == 0:
                excluded_count += 1
                continue

            # 只允许body/subheadline候选
            if block.type_candidate in [BlockType.BODY, BlockType.SUBHEADLINE]:
                candidates.append(block)
            else:
                excluded_count += 1

        logger.debug(f"Filtered {excluded_count} blocks, kept {len(candidates)} column candidates")
        return candidates

    def _try_gap_based_clustering(self, blocks: List[Block], page_width: float) -> bool:
        """
        基于gap的分栏（主策略）

        Args:
            blocks: 候选Block列表
            page_width: 页面宽度

        Returns:
            是否成功分栏
        """
        # 1. 按x坐标排序
        x_centers = sorted([b.bbox.center[0] for b in blocks])

        # 2. 计算相邻gap
        gaps = [x_centers[i + 1] - x_centers[i] for i in range(len(x_centers) - 1)]

        if not gaps:
            return False

        # 3. 计算gap统计
        median_gap = np.median(gaps)
        avg_gap = np.mean(gaps)

        logger.debug(f"Gap analysis: median={median_gap:.2f}, avg={avg_gap:.2f}")

        # 4. 找到大gap（分栏边界）
        threshold = median_gap * self.gap_threshold_multiplier
        boundaries = [
            i for i, gap in enumerate(gaps) if gap > threshold
        ]

        # 至少需要1个gap才能分栏
        if not boundaries:
            logger.info("No significant gaps found, treating as single column")
            for block in blocks:
                block.column = 0
            return True

        logger.info(f"Found {len(boundaries)} column boundaries at gaps: {[gaps[i] for i in boundaries]}")

        # 5. 根据边界分配栏号
        column_id = 0
        column_boundaries = [0] + [b + 1 for b in boundaries] + [len(x_centers)]

        for i in range(len(column_boundaries) - 1):
            start = column_boundaries[i]
            end = column_boundaries[i + 1]

            # 为该栏内的blocks分配column_id
            for j in range(start, end):
                if j < len(blocks):
                    blocks[j].column = column_id

            column_id += 1

        logger.info(f"Detected {column_id} columns using gap-based method (before width filter)")

        # 6. 应用最小栏宽约束，合并窄栏
        column_id = self._merge_narrow_columns(blocks, page_width)

        logger.info(f"After merging narrow columns: {column_id} columns")
        return True

    def _merge_narrow_columns(self, blocks: List[Block], page_width: float) -> int:
        """
        合并太窄的栏到相邻栏

        只考虑参与过分栏检测的blocks（即有column的正文blocks）

        Args:
            blocks: Block列表（已分配column）
            page_width: 页面宽度

        Returns:
            合并后的栏数
        """
        # 计算每个column的x坐标范围（只考虑正文blocks）
        column_x_ranges = {}
        column_block_counts = {}

        for block in blocks:
            if block.column is not None and block.char_count >= self.min_char_count:
                # 只统计满足字符数阈值的blocks（真正的正文blocks）
                if block.column not in column_x_ranges:
                    column_x_ranges[block.column] = []
                    column_block_counts[block.column] = 0
                column_x_ranges[block.column].append(block.bbox.center[0])
                column_block_counts[block.column] += 1

        # 如果没有正文blocks，直接返回
        if not column_x_ranges:
            return len(set(b.column for b in blocks if b.column is not None))

        # 计算每个column的宽度（基于正文blocks）
        column_widths = {}
        for col_id, x_centers in column_x_ranges.items():
            min_x = min(x_centers)
            max_x = max(x_centers)
            width = max_x - min_x
            column_widths[col_id] = width

        # 检查最小栏宽阈值
        min_width = page_width * self.min_column_width_ratio

        logger.debug(f"Column widths (based on text blocks >= {self.min_char_count} chars): {column_widths}")
        logger.debug(f"Column block counts: {column_block_counts}")
        logger.debug(f"Minimum width threshold: {min_width:.2f} ({self.min_column_width_ratio * 100}% of page width {page_width:.2f})")

        # 找出需要合并的窄栏
        narrow_columns = [
            col_id for col_id, width in column_widths.items()
            if width < min_width
        ]

        if not narrow_columns:
            # 没有窄栏，返回当前栏数
            return len(column_widths)

        logger.info(f"Found {len(narrow_columns)} narrow columns to merge: {narrow_columns}")

        # 合并窄栏到相邻栏
        # 策略：优先合并到左边，如果左边没有就合并到右边
        merged_count = 0
        for narrow_col in sorted(narrow_columns):
            # 找出相邻的栏（只考虑有正文blocks的栏）
            all_cols = sorted(column_widths.keys())
            idx = all_cols.index(narrow_col)

            # 优先合并到左边
            if idx > 0:
                target_col = all_cols[idx - 1]
            else:
                # 没有左边，合并到右边
                target_col = all_cols[idx + 1] if idx + 1 < len(all_cols) else narrow_col

            # 合并：将该栏的所有blocks重新分配到目标栏
            for block in blocks:
                if block.column == narrow_col:
                    block.column = target_col

            logger.debug(f"Merged column {narrow_col} (width={column_widths[narrow_col]:.1f}pt) into {target_col}")
            merged_count += 1

        # 重新编号栏号（0, 1, 2, ...）
        unique_columns = sorted(set(b.column for b in blocks if b.column is not None))
        column_mapping = {old: new for new, old in enumerate(unique_columns)}

        for block in blocks:
            if block.column is not None:
                block.column = column_mapping[block.column]

        logger.info(f"Merged {merged_count} narrow columns, final count: {len(unique_columns)}")
        return len(unique_columns)

    def _assign_columns_to_zone(
        self, zone_blocks: List[Block], candidate_blocks: List[Block], base_col: int = 0
    ):
        """
        将column信息从候选blocks扩展到该zone的所有blocks

        Args:
            zone_blocks: 该zone的所有blocks
            candidate_blocks: 已分配column的候选blocks
            base_col: 该zone的起始column编号
        """
        # 创建候选blocks的column映射（使用相对column编号）
        column_x_ranges = {}

        for block in candidate_blocks:
            if block.column is not None:
                # 将相对column编号转换为绝对编号
                abs_col = base_col + block.column
                block.column = abs_col

                if abs_col not in column_x_ranges:
                    column_x_ranges[abs_col] = []

                column_x_ranges[abs_col].append(block.bbox.center[0])

        # 计算每个column的x坐标范围
        column_ranges = {}
        for col_id, x_centers in column_x_ranges.items():
            min_x = min(x_centers)
            max_x = max(x_centers)
            column_ranges[col_id] = (min_x, max_x)

        # 为该zone的所有blocks分配column
        for block in zone_blocks:
            if block.column is not None:
                continue  # 已分配（是candidate block）

            # 根据x坐标判断column
            block_x = block.bbox.center[0]

            # 找到最接近的column
            best_column = base_col  # 默认使用该zone的起始column
            min_distance = float("inf")

            for col_id, (min_x, max_x) in column_ranges.items():
                # 计算到column中心的距离
                column_center = (min_x + max_x) / 2
                distance = abs(block_x - column_center)

                if distance < min_distance:
                    min_distance = distance
                    best_column = col_id

            block.column = best_column

        logger.debug(f"Assigned columns to zone with base_col={base_col}: {len(zone_blocks)} blocks")

    def _kmeans_clustering_zone(self, zone_blocks: List[Block], page_width: float, base_col: int = 0) -> List[Block]:
        """
        KMeans聚类分栏（兜底策略，zone版本）

        Args:
            zone_blocks: 该zone的blocks
            page_width: 页面宽度
            base_col: 该zone的起始column编号

        Returns:
            更新了column信息的Block列表
        """
        # 使用相同的过滤逻辑
        candidate_blocks = self._filter_column_candidates(zone_blocks)

        if len(candidate_blocks) < 2:
            for block in zone_blocks:
                block.column = base_col
            return zone_blocks

        x_centers = [b.bbox.center[0] for b in candidate_blocks]

        # 估计栏数（限制在合理范围）
        estimated_cols = self._estimate_column_count(x_centers)
        estimated_cols = max(1, min(estimated_cols, 4))  # 每个zone最多4栏

        # 使用KMeans聚类
        try:
            x_array = np.array(x_centers).reshape(-1, 1)
            kmeans = KMeans(n_clusters=estimated_cols, random_state=42, n_init=10)
            labels = kmeans.fit_predict(x_array)

            # 按聚类中心的位置排序label（确保从左到右）
            cluster_centers = kmeans.cluster_centers_.flatten()
            sorted_indices = np.argsort(cluster_centers)
            label_mapping = {old: new for new, old in enumerate(sorted_indices)}

            # 分配column（使用相对编号）
            for block, label in zip(candidate_blocks, labels):
                block.column = label_mapping[label]

            # 应用最小栏宽约束（使用相对编号）
            self._merge_narrow_columns(candidate_blocks, page_width)

            # 转换为绝对column编号
            for block in candidate_blocks:
                if block.column is not None:
                    block.column = base_col + block.column

            # 为该zone的其他blocks分配column
            self._assign_columns_to_zone(zone_blocks, candidate_blocks, base_col)

            return zone_blocks

        except Exception as e:
            logger.error(f"KMeans clustering failed: {e}, treating as single column")
            for block in zone_blocks:
                block.column = base_col
            return zone_blocks

    def _assign_columns_to_all(
        self, all_blocks: List[Block], candidate_blocks: List[Block]
    ):
        """
        将column信息从候选blocks扩展到所有blocks

        Args:
            all_blocks: 所有blocks
            candidate_blocks: 已分配column的候选blocks
        """
        # 创建候选blocks的column映射
        # 使用x坐标范围来判断column
        column_x_ranges = {}

        for block in candidate_blocks:
            if block.column is not None:
                if block.column not in column_x_ranges:
                    column_x_ranges[block.column] = []

                column_x_ranges[block.column].append(block.bbox.center[0])

        # 计算每个column的x坐标范围
        column_ranges = {}
        for col_id, x_centers in column_x_ranges.items():
            min_x = min(x_centers)
            max_x = max(x_centers)
            column_ranges[col_id] = (min_x, max_x)

        # 为所有blocks分配column
        for block in all_blocks:
            if block.column is not None:
                continue  # 已分配

            if block.type_final == BlockType.IMAGE:
                # 图片：找最近的column
                block.column = self._find_nearest_column(block, candidate_blocks)
                continue

            # 根据x坐标判断column
            block_x = block.bbox.center[0]

            # 找到最接近的column
            best_column = 0
            min_distance = float("inf")

            for col_id, (min_x, max_x) in column_ranges.items():
                # 计算到column中心的距离
                column_center = (min_x + max_x) / 2
                distance = abs(block_x - column_center)

                if distance < min_distance:
                    min_distance = distance
                    best_column = col_id

            block.column = best_column

        logger.debug(f"Assigned columns to all {len(all_blocks)} blocks")

    def _find_nearest_column(
        self, block: Block, candidate_blocks: List[Block]
    ) -> int:
        """
        为block找最近的column

        Args:
            block: 要查找的block
            candidate_blocks: 已分配column的blocks

        Returns:
            栏号
        """
        min_dist = float("inf")
        nearest_col = 0

        for other in candidate_blocks:
            if other.column is not None:
                dist = self._calculate_horizontal_distance(block.bbox, other.bbox)
                if dist < min_dist:
                    min_dist = dist
                    nearest_col = other.column

        return nearest_col

    def _calculate_horizontal_distance(self, bbox1, bbox2) -> float:
        """计算水平距离"""
        c1 = bbox1.center[0]
        c2 = bbox2.center[0]
        return abs(c1 - c2)

    def _kmeans_clustering(self, blocks: List[Block], page_width: float) -> List[Block]:
        """
        KMeans聚类分栏（兜底策略）

        Args:
            blocks: Block列表
            page_width: 页面宽度

        Returns:
            更新了column信息的Block列表
        """
        logger.info("Using KMeans clustering for column detection")

        # 使用相同的过滤逻辑
        candidate_blocks = self._filter_column_candidates(blocks)

        if len(candidate_blocks) < 2:
            for block in blocks:
                block.column = 0
            return blocks

        x_centers = [b.bbox.center[0] for b in candidate_blocks]

        # 估计栏数（限制在合理范围）
        estimated_cols = self._estimate_column_count(x_centers)
        estimated_cols = max(2, min(estimated_cols, 8))  # 限制在2-8栏之间

        # 使用KMeans聚类
        try:
            x_array = np.array(x_centers).reshape(-1, 1)
            kmeans = KMeans(n_clusters=estimated_cols, random_state=42, n_init=10)
            labels = kmeans.fit_predict(x_array)

            # 按聚类中心的位置排序label（确保从左到右）
            cluster_centers = kmeans.cluster_centers_.flatten()
            sorted_indices = np.argsort(cluster_centers)
            label_mapping = {old: new for new, old in enumerate(sorted_indices)}

            # 分配column
            for block, label in zip(candidate_blocks, labels):
                block.column = label_mapping[label]

            # 应用最小栏宽约束
            self._merge_narrow_columns(candidate_blocks, page_width)

            # 为其他blocks分配column
            self._assign_columns_to_all(blocks, candidate_blocks)

            logger.info(f"Detected {len(set(b.column for b in candidate_blocks if b.column is not None))} columns using KMeans")
            return blocks

        except Exception as e:
            logger.error(f"KMeans clustering failed: {e}, treating as single column")
            for block in blocks:
                block.column = 0
            return blocks

    def _estimate_column_count(self, x_centers: List[float]) -> int:
        """估计栏数"""
        if len(x_centers) <= 3:
            return len(set(x_centers))

        # 简单策略：基于x坐标的分布
        unique_x = sorted(set(round(x, 1) for x in x_centers))

        if len(unique_x) <= 3:
            return len(unique_x)

        # 计算相邻x坐标的间距
        gaps = [unique_x[i + 1] - unique_x[i] for i in range(len(unique_x) - 1)]
        avg_gap = sum(gaps) / len(gaps)

        # 间距明显大于平均gap的地方是栏的边界
        column_boundaries = [0]
        for i, gap in enumerate(gaps):
            if gap > avg_gap * 0.8:
                column_boundaries.append(i + 1)

        return len(column_boundaries)
