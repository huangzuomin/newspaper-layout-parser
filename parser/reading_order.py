"""
阅读顺序构建器（双层顺序）
Reading Order Builder - Build block-level and article-level reading order
"""

from typing import List, Tuple
import logging

from .schema import Block, Article, ZoneType

logger = logging.getLogger("parser")


class ReadingOrderBuilder:
    """阅读顺序构建器"""

    # Zone优先级
    ZONE_PRIORITY = {
        ZoneType.MASTHEAD: 0,
        ZoneType.HEADLINE_ZONE: 1,
        ZoneType.LEFT_ZONE: 2,
        ZoneType.RIGHT_ZONE: 3,
        ZoneType.BOTTOM_ZONE: 4,
    }

    def build(
        self, blocks: List[Block], articles: List[Article]
    ) -> Tuple[List[str], List[str]]:
        """
        构建双层阅读顺序

        Args:
            blocks: Block列表
            articles: Article列表

        Returns:
            (block_reading_order, article_reading_order)
        """
        logger.info("Building reading order...")

        # 1. 构建Block级阅读顺序
        block_order = self._build_block_order(blocks)
        logger.info(f"Block reading order: {len(block_order)} blocks")

        # 2. 构建Article级阅读顺序
        article_order = self._build_article_order(articles, blocks, block_order)
        logger.info(f"Article reading order: {len(article_order)} articles")

        return block_order, article_order

    def _build_block_order(self, blocks: List[Block]) -> List[str]:
        """
        构建Block级阅读顺序

        Args:
            blocks: Block列表

        Returns:
            block ID列表（按阅读顺序）
        """
        # 按zone分组
        zone_blocks = {}
        for block in blocks:
            zone = block.zone or ZoneType.LEFT_ZONE
            if zone not in zone_blocks:
                zone_blocks[zone] = []
            zone_blocks[zone].append(block)

        # 按zone优先级排序
        ordered_zones = sorted(
            zone_blocks.keys(),
            key=lambda z: self.ZONE_PRIORITY.get(z, 999)
        )

        reading_order = []

        for zone in ordered_zones:
            zone_blocks_list = zone_blocks[zone]

            # 特殊处理：right_zone作为整体
            if zone == ZoneType.RIGHT_ZONE:
                # 按column排序，然后按y排序
                zone_blocks_list = sorted(
                    zone_blocks_list,
                    key=lambda b: (b.column if b.column is not None else 0, b.bbox.center[1])
                )
            else:
                # 其他zone按y坐标排序
                zone_blocks_list = sorted(
                    zone_blocks_list,
                    key=lambda b: b.bbox.center[1]
                )

            # 添加到阅读顺序
            for block in zone_blocks_list:
                if block.id not in reading_order:
                    reading_order.append(block.id)

        return reading_order

    def _build_article_order(
        self,
        articles: List[Article],
        blocks: List[Block],
        block_order: List[str]
    ) -> List[str]:
        """
        构建Article级阅读顺序

        Args:
            articles: Article列表
            blocks: Block列表
            block_order: Block级阅读顺序

        Returns:
            article ID列表（按阅读顺序）
        """
        # 创建block ID到索引的映射
        block_id_to_index = {
            block_id: idx
            for idx, block_id in enumerate(block_order)
        }

        # 找到每个article的第一个block在block_order中的位置
        article_positions = []

        for article in articles:
            # 尝试找到headline的位置
            first_block_id = article.headline_block_id

            # 如果没有headline，使用第一个body
            if not first_block_id and article.body_block_ids:
                first_block_id = article.body_block_ids[0]

            if first_block_id and first_block_id in block_id_to_index:
                position = block_id_to_index[first_block_id]
                article_positions.append((position, article.id))
            else:
                # 如果找不到位置，放在最后
                article_positions.append((float('inf'), article.id))

        # 按位置排序
        article_positions.sort(key=lambda x: x[0])

        # 提取article IDs
        article_order = [article_id for _, article_id in article_positions]

        return article_order

    def insert_articles_into_block_order(
        self,
        block_order: List[str],
        article_order: List[str],
        articles: List[Article]
    ) -> List[str]:
        """
        将article标记插入到block阅读顺序中（用于可视化）

        Args:
            block_order: Block级阅读顺序
            article_order: Article级阅读顺序
            articles: Article列表

        Returns:
            增强后的阅读顺序（包含article标记）
        """
        # 创建block到article的映射
        block_to_article = {}
        for article in articles:
            if article.headline_block_id:
                block_to_article[article.headline_block_id] = article.id
            for body_id in article.body_block_ids:
                block_to_article[body_id] = article.id

        # 创建article顺序映射
        article_to_index = {
            article_id: idx
            for idx, article_id in enumerate(article_order)
        }

        # 在block顺序中插入article标记
        enhanced_order = []
        last_article_index = -1

        for block_id in block_order:
            # 检查是否是article的开始
            if block_id in block_to_article:
                article_id = block_to_article[block_id]
                article_index = article_to_index.get(article_id, -1)

                # 如果是新的article，添加标记
                if article_index > last_article_index:
                    enhanced_order.append(f"--- ARTICLE: {article_id} ---")
                    last_article_index = article_index

            enhanced_order.append(block_id)

        return enhanced_order
