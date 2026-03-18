"""
Block分类器（两阶段分类）
Block Classifier - Two-stage block classification
"""

from typing import List, Dict, Tuple, Optional
import logging

from .schema import Block, BlockType
from .font_analyzer import FontAnalyzer

logger = logging.getLogger("parser")


class BlockClassifier:
    """Block分类器（两阶段）"""

    # Section label关键词
    SECTION_LABELS = [
        ">>>",
        "编者按",
        "本期关注",
        "要闻",
        "责任编辑",
        "本报讯",
        "新华社",
        "人民日报",
    ]

    def __init__(self):
        """初始化分类器"""
        self.font_analyzer = FontAnalyzer()

    def classify_candidates(
        self, blocks: List[Block], font_profile: Dict
    ) -> List[Block]:
        """
        第一阶段：候选分类（宽松条件）

        Args:
            blocks: Block列表
            font_profile: 字体配置

        Returns:
            更新了type_candidate的Block列表
        """
        logger.info("Stage 1: Candidate classification")

        # 获取正文字体大小
        body_avg_size = font_profile.get("body", (0, 0, 11))[2]

        type_counts = {}

        for block in blocks:
            # 跳过图片
            if block.type_final == BlockType.IMAGE:
                block.type_candidate = BlockType.IMAGE
                continue

            candidates = []
            reasons = []

            # 特殊处理：right_zone中的大字号短文本优先考虑headline
            from .schema import ZoneType
            is_right_zone = block.zone == ZoneType.RIGHT_ZONE
            is_large_font = block.font_size >= body_avg_size * 1.4
            is_short_text = block.lines_count <= 3 and block.char_count < 30

            if is_right_zone and is_large_font and is_short_text:
                # right_zone的大字号短文本强制判定为headline候选
                candidates.append(BlockType.HEADLINE)
                reasons.append(f"Right zone large font ({block.font_size:.1f}pt) short text - priority headline")

            # 1. 检查section label（关键词匹配）
            # 但在right_zone中降低优先级
            if self._is_section_label(block):
                if not is_right_zone or not (is_large_font and is_short_text):
                    candidates.append(BlockType.SECTION_LABEL)
                    reasons.append("Contains section label keywords")

            # 2. 检查caption（小字体+靠近图片）
            if self._is_caption_candidate(block, blocks):
                candidates.append(BlockType.CAPTION)
                reasons.append("Small font + near image")

            # 3. 检查headline（大字体+少行数）
            if self._is_headline_candidate(block, body_avg_size):
                candidates.append(BlockType.HEADLINE)
                reasons.append(f"Font size {block.font_size:.1f} >= body_avg * 1.4")

            # 4. 检查subheadline（中等字体+少行数）
            if self._is_subheadline_candidate(block, body_avg_size):
                candidates.append(BlockType.SUBHEADLINE)
                reasons.append(f"Font size {block.font_size:.1f} >= body_avg * 1.15")

            # 5. 检查body（多行+正常字体）
            if self._is_body_candidate(block, body_avg_size):
                candidates.append(BlockType.BODY)
                reasons.append("Normal font + multiple lines")

            # 记录候选类型
            if candidates:
                # 优先级：right_zone中headline优先，否则 section_label > headline > subheadline > caption > body
                if is_right_zone and BlockType.HEADLINE in candidates:
                    block.type_candidate = BlockType.HEADLINE
                else:
                    priority_order = [
                        BlockType.SECTION_LABEL,
                        BlockType.HEADLINE,
                        BlockType.SUBHEADLINE,
                        BlockType.CAPTION,
                        BlockType.BODY,
                    ]

                    for priority_type in priority_order:
                        if priority_type in candidates:
                            block.type_candidate = priority_type
                            break
            else:
                block.type_candidate = BlockType.OTHER
                reasons.append("No matching type")

            block.classification_reasons = reasons

            # 统计
            type_value = block.type_candidate.value if block.type_candidate else "unknown"
            type_counts[type_value] = type_counts.get(type_value, 0) + 1

        logger.info(f"Candidate classification results: {type_counts}")
        return blocks

    def _is_section_label(self, block: Block) -> bool:
        """判断是否为栏目标签

        真正的section_label特征：
        1. 短文本（通常<15字符）
        2. 少行数（通常1-2行）
        3. 特殊格式（">>>2版"、"版"字结尾）
        4. 或明确的标签词（"编者按"、"本期关注"等）
        """
        text = block.text.strip()

        # 规则1: 特殊格式标记（如">>>2版"、"瓯宝到家>>>"）
        if ">>>" in text:
            # 箭头标记的通常都是版面引导标签
            return True

        # 规则2: 明确的短标签词
        short_labels = ["编者按", "本期关注"]
        for label in short_labels:
            if text == label or text.startswith(label + "："):
                # 必须是短文本（<15字符）且少行（<=3行）
                if block.char_count < 15 and block.lines_count <= 3:
                    return True

        # 规则3: 版面引导（如"2版"、"第8版"）
        if "版" in text and block.char_count < 10 and block.lines_count == 1:
            return True

        # 不再匹配宽泛的关键词（如"要闻"、"新华社"）
        # 因为这些词经常出现在正文中

        return False

    def _is_caption_candidate(self, block: Block, all_blocks: List[Block]) -> bool:
        """判断是否为图注"""
        # 条件1：字体较小
        if block.font_size > 9:
            return False

        # 条件2：靠近图片（距离判断）
        for other in all_blocks:
            if other.type_final == BlockType.IMAGE:
                distance = self._calculate_distance(block.bbox, other.bbox)
                if distance < 50:  # 50像素内
                    return True

        return False

    def _is_headline_candidate(self, block: Block, body_avg_size: float) -> bool:
        """判断是否为主标题候选"""
        # 条件1：字体明显大于正文
        if block.font_size < body_avg_size * 1.4:
            return False

        # 条件2：行数不超过3行，但有特殊情况处理
        # 如果lines_count异常大（可能是竖排文字或每个字符都是独立的line），则基于字符数判断
        if block.lines_count > 3:
            # 检查是否是异常情况：lines_count约等于char_count
            # 这种情况说明每个字符被当作一行，需要修正判断
            if block.lines_count >= block.char_count * 0.8:
                # 异常情况：基于字符数判断（短文本可能是headline）
                if block.char_count <= 80:  # 短文本
                    return True
                return False
            # 正常情况：行数确实太多，不是headline
            return False

        # 条件3：字符数不超过100
        if block.char_count > 100:
            return False

        return True

    def _is_subheadline_candidate(self, block: Block, body_avg_size: float) -> bool:
        """判断是否为副标题候选"""
        # 条件1：字体大于正文
        if block.font_size < body_avg_size * 1.15:
            return False

        # 条件2：行数不超过3行
        if block.lines_count > 3:
            return False

        # 条件3：但小于headline的标准
        if block.font_size >= body_avg_size * 1.4:
            return False

        return True

    def _is_body_candidate(self, block: Block, body_avg_size: float) -> bool:
        """判断是否为正文候选"""
        # 条件1：字体在正文范围内（±30%）
        if not (body_avg_size * 0.7 <= block.font_size <= body_avg_size * 1.3):
            return False

        # 条件2：字符数较多
        if block.char_count < 20:
            return False

        # 条件3：行数至少2行
        if block.lines_count < 2:
            return False

        return True

    def _calculate_distance(self, bbox1, bbox2) -> float:
        """计算两个bbox之间的最短距离"""
        # 计算中心点距离
        c1 = bbox1.center
        c2 = bbox2.center
        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5

    def finalize_classification(self, blocks: List[Block]) -> List[Block]:
        """
        第二阶段：最终分类（结合上下文）

        Args:
            blocks: Block列表

        Returns:
            更新了type_final的Block列表
        """
        logger.info("Stage 2: Final classification")

        type_counts = {}

        for block in blocks:
            # 图片直接使用IMAGE类型
            if block.type_candidate == BlockType.IMAGE:
                block.type_final = BlockType.IMAGE
                type_counts["image"] = type_counts.get("image", 0) + 1
                continue

            # 基于候选类型确定最终类型
            if block.type_candidate == BlockType.HEADLINE:
                # 验证：headline附近应有body
                if self._has_nearby_body(block, blocks):
                    block.type_final = BlockType.HEADLINE
                    block.classification_reasons.append("Final: Confirmed as headline")
                else:
                    # 降级为subheadline
                    block.type_final = BlockType.SUBHEADLINE
                    block.classification_reasons.append(
                        "Final: Downgraded to subheadline (no nearby body)"
                    )

            elif block.type_candidate == BlockType.SUBHEADLINE:
                block.type_final = BlockType.SUBHEADLINE
                block.classification_reasons.append("Final: Confirmed as subheadline")

            elif block.type_candidate == BlockType.BODY:
                block.type_final = BlockType.BODY
                block.classification_reasons.append("Final: Confirmed as body")

            elif block.type_candidate == BlockType.CAPTION:
                block.type_final = BlockType.CAPTION
                block.classification_reasons.append("Final: Confirmed as caption")

            elif block.type_candidate == BlockType.SECTION_LABEL:
                block.type_final = BlockType.SECTION_LABEL
                block.classification_reasons.append("Final: Confirmed as section label")

            else:
                block.type_final = BlockType.OTHER
                block.classification_reasons.append("Final: No type matched")

            # 统计
            type_value = block.type_final.value if block.type_final else "unknown"
            type_counts[type_value] = type_counts.get(type_value, 0) + 1

        logger.info(f"Final classification results: {type_counts}")
        return blocks

    def _has_nearby_body(self, block: Block, all_blocks: List[Block]) -> bool:
        """
        检查block附近是否有body类型的候选

        Args:
            block: 要检查的block
            all_blocks: 所有blocks

        Returns:
            是否有附近的body候选
        """
        block_bottom = block.bbox.y1

        for other in all_blocks:
            if other.type_candidate == BlockType.BODY:
                # 检查是否在block下方且距离合理
                if other.bbox.y0 > block_bottom:
                    distance = other.bbox.y0 - block_bottom
                    if distance < 200:  # 200像素内
                        return True

        return False
