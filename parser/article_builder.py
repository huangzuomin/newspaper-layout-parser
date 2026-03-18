"""
文章构建器（基于headline候选）
Article Builder - Cluster blocks into articles based on headline candidates
"""

from typing import List, Dict, Optional
import logging

from .schema import Block, Article, BlockType, ZoneType

logger = logging.getLogger("parser")


class ArticleBuilder:
    """文章构建器"""

    def __init__(self):
        """初始化文章构建器"""
        # 文章构建参数
        self.max_distance_below_headline = 500  # 像素
        self.max_distance_to_article = 200  # 像素

    def build(self, blocks: List[Block]) -> List[Article]:
        """
        构建文章

        Args:
            blocks: Block列表（已分类和分栏）

        Returns:
            Article列表
        """
        logger.info("Building articles...")

        articles = []

        # 按zone分组处理
        zones = [
            ZoneType.RIGHT_ZONE,
            ZoneType.LEFT_ZONE,
            ZoneType.HEADLINE_ZONE,
            ZoneType.BOTTOM_ZONE,
        ]

        for zone in zones:
            zone_blocks = [b for b in blocks if b.zone == zone]

            if not zone_blocks:
                continue

            logger.debug(f"Processing {zone.value} ({len(zone_blocks)} blocks)")

            # 跳过masthead（报头区不构建文章）
            if zone == ZoneType.MASTHEAD:
                continue

            # 识别该zone的headline candidates
            headlines = [
                b for b in zone_blocks
                if b.type_candidate == BlockType.HEADLINE
            ]

            logger.debug(f"Found {len(headlines)} headline candidates in {zone.value}")

            # 根据headline数量决定构建策略
            if len(headlines) > 1:
                # 策略1：多个headline，分别构建文章
                zone_articles = self._build_multiple_headline_articles(
                    headlines, zone_blocks, zone
                )
            elif len(headlines) == 1:
                # 策略2：单个headline，构建整zone文章
                zone_articles = self._build_single_headline_article(
                    headlines[0], zone_blocks, zone
                )
            else:
                # 策略3：没有headline，所有body归为一篇文章
                zone_articles = self._build_body_only_article(zone_blocks, zone)

            articles.extend(zone_articles)

        # 关联图片和图注到文章
        self._associate_images_and_captions(articles, blocks)

        logger.info(f"Built {len(articles)} articles")
        return articles

    def _build_multiple_headline_articles(
        self, headlines: List[Block], zone_blocks: List[Block], zone: ZoneType
    ) -> List[Article]:
        """
        构建多个headline的文章

        Args:
            headlines: headline blocks列表
            zone_blocks: 该zone的所有blocks
            zone: zone类型

        Returns:
            Article列表
        """
        articles = []

        for i, headline in enumerate(headlines):
            # 找到该headline下方的body blocks
            body_blocks = self._find_body_below_headline(headline, zone_blocks)

            # 检查是否有subheadline
            subheadline = self._find_subheadline(headline, zone_blocks)

            # 检查是否有caption
            captions = self._find_nearby_captions(headline, zone_blocks)

            article_id = f"a_{zone.value.lower()}_{i + 1}"

            article = Article(
                id=article_id,
                headline_block_id=headline.id,
                subheadline_block_id=subheadline.id if subheadline else None,
                body_block_ids=[b.id for b in body_blocks],
                caption_block_ids=[c.id for c in captions],
                image_block_ids=[],
                zone=zone,
                confidence=1.0,
                match_reasons=[
                    f"Multiple headline article #{i + 1}",
                    f"Headline: {headline.text[:30]}...",
                    f"Body blocks: {len(body_blocks)}",
                ],
            )

            articles.append(article)
            logger.debug(f"  Article {article_id}: headline={headline.id}, body={len(body_blocks)}")

        return articles

    def _build_single_headline_article(
        self, headline: Block, zone_blocks: List[Block], zone: ZoneType
    ) -> List[Article]:
        """
        构建单个headline的整zone文章

        Args:
            headline: headline block
            zone_blocks: 该zone的所有blocks
            zone: zone类型

        Returns:
            Article列表（包含1个article）
        """
        # 收集所有body blocks
        body_blocks = [b for b in zone_blocks if b.type_candidate == BlockType.BODY]

        # 找到subheadline
        subheadline = self._find_subheadline(headline, zone_blocks)

        # 找到captions
        captions = [b for b in zone_blocks if b.type_candidate == BlockType.CAPTION]

        article_id = f"a_{zone.value.lower()}_1"

        article = Article(
            id=article_id,
            headline_block_id=headline.id,
            subheadline_block_id=subheadline.id if subheadline else None,
            body_block_ids=[b.id for b in body_blocks],
            caption_block_ids=[c.id for c in captions],
            image_block_ids=[],
            zone=zone,
            confidence=1.0,
            match_reasons=[
                f"Single headline article",
                f"Headline: {headline.text[:30]}...",
                f"Whole zone article with {len(body_blocks)} body blocks",
            ],
        )

        logger.debug(f"  Article {article_id}: headline={headline.id}, body={len(body_blocks)}")
        return [article]

    def _build_body_only_article(
        self, zone_blocks: List[Block], zone: ZoneType
    ) -> List[Article]:
        """
        构建无headline的body文章

        Args:
            zone_blocks: 该zone的所有blocks
            zone: zone类型

        Returns:
            Article列表（包含1个article）
        """
        # 收集所有body blocks
        body_blocks = [b for b in zone_blocks if b.type_candidate == BlockType.BODY]

        if not body_blocks:
            logger.warning(f"No body blocks found in {zone.value}")
            return []

        # 找到captions
        captions = [b for b in zone_blocks if b.type_candidate == BlockType.CAPTION]

        article_id = f"a_{zone.value.lower()}_noheadline"

        article = Article(
            id=article_id,
            headline_block_id=None,
            subheadline_block_id=None,
            body_block_ids=[b.id for b in body_blocks],
            caption_block_ids=[c.id for c in captions],
            image_block_ids=[],
            zone=zone,
            confidence=0.7,  # 降低置信度，因为没有headline
            match_reasons=[
                f"No headline found",
                f"Body-only article with {len(body_blocks)} blocks",
            ],
        )

        logger.debug(f"  Article {article_id}: body={len(body_blocks)} (no headline)")
        return [article]

    def _find_body_below_headline(
        self, headline: Block, zone_blocks: List[Block]
    ) -> List[Block]:
        """
        找到headline附近的正文块（包括上方和下方）

        Args:
            headline: headline block
            zone_blocks: 该zone的所有blocks

        Returns:
            body blocks列表
        """
        body_blocks = []
        headline_top = headline.bbox.y0
        headline_bottom = headline.bbox.y1

        for block in zone_blocks:
            if block.type_candidate != BlockType.BODY:
                continue

            # 检查是否在headline下方
            if block.bbox.y0 > headline_bottom:
                distance = block.bbox.y0 - headline_bottom

                # 距离合理且在同一column
                if distance < self.max_distance_below_headline:
                    # 优先选择同column的blocks
                    if block.column == headline.column:
                        body_blocks.append(block)
                    elif distance < self.max_distance_below_headline * 0.5:
                        # 距离很近的也加入
                        body_blocks.append(block)

            # 检查是否在headline上方（新增）
            elif block.bbox.y1 < headline_top:
                distance = headline_top - block.bbox.y1

                # 上方距离合理（通常是正文在前，标题在后）
                if distance < self.max_distance_below_headline:
                    # 优先选择同column的blocks
                    if block.column == headline.column:
                        body_blocks.append(block)
                    elif distance < self.max_distance_below_headline * 0.5:
                        # 距离很近的也加入
                        body_blocks.append(block)

        return body_blocks

    def _find_subheadline(
        self, headline: Block, zone_blocks: List[Block]
    ) -> Optional[Block]:
        """
        找到headline对应的subheadline

        Args:
            headline: headline block
            zone_blocks: 该zone的所有blocks

        Returns:
            subheadline block或None
        """
        headline_bottom = headline.bbox.y1

        for block in zone_blocks:
            if block.type_candidate != BlockType.SUBHEADLINE:
                continue

            # subheadline应该在headline附近（下方100像素内）
            if headline_bottom < block.bbox.y0 < headline_bottom + 100:
                return block

        return None

    def _find_nearby_captions(
        self, headline: Block, zone_blocks: List[Block]
    ) -> List[Block]:
        """
        找到headline附近的captions

        Args:
            headline: headline block
            zone_blocks: 该zone的所有blocks

        Returns:
            caption blocks列表
        """
        captions = []
        headline_center = headline.bbox.center

        for block in zone_blocks:
            if block.type_candidate != BlockType.CAPTION:
                continue

            # 计算距离
            distance = (
                (headline_center[0] - block.bbox.center[0]) ** 2
                + (headline_center[1] - block.bbox.center[1]) ** 2
            ) ** 0.5

            if distance < 200:  # 200像素内
                captions.append(block)

        return captions

    def _associate_images_and_captions(
        self, articles: List[Article], blocks: List[Block]
    ):
        """
        关联图片和图注到文章

        Args:
            articles: Article列表
            blocks: Block列表
        """
        # 创建block到article的映射
        block_to_article = {}
        for article in articles:
            if article.headline_block_id:
                block_to_article[article.headline_block_id] = article
            for body_id in article.body_block_ids:
                block_to_article[body_id] = article

        # 处理每个图片
        for block in blocks:
            if block.type_candidate != BlockType.IMAGE:
                continue

            # 找到最近的文章
            nearest_article = self._find_nearest_article(block, articles, blocks)
            if nearest_article and block.id not in nearest_article.image_block_ids:
                nearest_article.image_block_ids.append(block.id)
                nearest_article.match_reasons.append(
                    f"Associated image {block.id}"
                )

        # 处理每个图注（已包含在article中，这里只是验证）
        for article in articles:
            # 图注已经在构建时关联了
            if article.caption_block_ids:
                article.match_reasons.append(
                    f"Associated {len(article.caption_block_ids)} captions"
                )

    def _find_nearest_article(
        self, image_block: Block, articles: List[Article], all_blocks: List[Block]
    ) -> Optional[Article]:
        """
        为图片找最近的文章

        Args:
            image_block: 图片block
            articles: Article列表
            all_blocks: 所有blocks

        Returns:
            最近的Article或None
        """
        min_dist = float("inf")
        nearest_article = None

        for article in articles:
            # 计算与article中所有block的距离
            for block_id in [article.headline_block_id] + article.body_block_ids:
                if not block_id:
                    continue

                target_block = next((b for b in all_blocks if b.id == block_id), None)
                if target_block:
                    dist = self._calculate_distance(image_block.bbox, target_block.bbox)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_article = article

        return nearest_article if min_dist < 200 else None

    def _calculate_distance(self, bbox1, bbox2) -> float:
        """计算bbox之间的距离"""
        c1 = bbox1.center
        c2 = bbox2.center
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5
