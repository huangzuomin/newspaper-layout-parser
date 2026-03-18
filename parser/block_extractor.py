"""
文本块提取器
Block Extractor - Extract blocks from PDF pages using PyMuPDF
"""

import fitz
from typing import List, Optional
import logging

from .schema import Block, BBox, BlockType

logger = logging.getLogger("parser")


class BlockExtractor:
    """从PDF页面提取文本块"""

    def extract_blocks(self, page: fitz.Page, page_no: int) -> List[Block]:
        """
        从页面提取所有文本块

        Args:
            page: PyMuPDF页面对象
            page_no: 页码（0-based）

        Returns:
            Block对象列表
        """
        logger.debug(f"Extracting blocks from page {page_no}")

        blocks = []

        # 使用dict模式提取完整的文本结构
        try:
            page_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
        except Exception as e:
            logger.error(f"Failed to extract text dict from page {page_no}: {e}")
            return blocks

        block_id = 0

        # 遍历所有blocks
        for block_no, block in enumerate(page_dict.get("blocks", [])):
            if block["type"] == 0:  # 文本块
                block_obj = self._parse_text_block(block, page_no, block_no, block_id)
                if block_obj:
                    blocks.append(block_obj)
                    block_id += 1
            elif block["type"] == 1:  # 图片块
                block_obj = self._parse_image_block(block, page_no, block_no, block_id)
                if block_obj:
                    blocks.append(block_obj)
                    block_id += 1

        logger.info(f"Extracted {len(blocks)} blocks from page {page_no}")
        return blocks

    def _parse_text_block(
        self, block: dict, page_no: int, block_no: int, block_id: int
    ) -> Optional[Block]:
        """
        解析文本块

        Args:
            block: PyMuPDF的block字典
            page_no: 页码
            block_no: PyMuPDF的block编号
            block_id: 自定义block ID

        Returns:
            Block对象或None
        """
        bbox = block["bbox"]
        lines = block.get("lines", [])

        if not lines:
            return None

        # 提取所有span信息
        all_spans = []
        all_font_sizes = []
        all_font_names = []
        total_chars = 0

        for line in lines:
            for span in line.get("spans", []):
                span_text = span["text"]
                span_font_size = span["size"]
                span_font_name = span["font"]
                span_flags = span.get("flags", 0)

                all_spans.append({
                    "text": span_text,
                    "font_size": span_font_size,
                    "font_name": span_font_name,
                    "flags": span_flags,
                    "color": span.get("color", 0),
                })

                all_font_sizes.append(span_font_size)
                all_font_names.append(span_font_name)
                total_chars += len(span_text)

        # 如果没有有效的span，跳过
        if not all_spans:
            return None

        # 计算主字体（取中位数）
        avg_font_size = sum(all_font_sizes) / len(all_font_sizes)
        sorted_sizes = sorted(all_font_sizes)
        median_font_size = sorted_sizes[len(sorted_sizes) // 2]

        # 获取最常见的字体名
        from collections import Counter
        font_name_counts = Counter(all_font_names)
        most_common_font = font_name_counts.most_common(1)[0][0]

        # 检测粗体（flags & 2^4 表示粗体）
        is_bold = any(span.get("flags", 0) & 16 for span in all_spans)

        # 提取文本
        raw_text = "".join([span["text"] for span in all_spans])
        text = raw_text.strip()

        # 计算行数
        lines_count = len(lines)

        # 计算字符数
        char_count = len(text)

        # 过滤过小的blocks
        if char_count < 3 and lines_count < 2:
            logger.debug(f"Skipping small block {block_id}: {char_count} chars, {lines_count} lines")
            return None

        # 生成block ID
        block_id_str = f"p{page_no}_b{block_id}"

        return Block(
            id=block_id_str,
            text=text,
            raw_text=raw_text,
            bbox=BBox(*bbox),
            font_size=median_font_size,
            font_name=most_common_font,
            font_sizes=all_font_sizes,
            font_names=all_font_names,
            source_block_no=block_no,
            type_candidate=None,
            type_final=None,
            classification_reasons=[],
            zone=None,
            column=None,
            lines_count=lines_count,
            char_count=char_count,
            is_bold=is_bold,
            confidence=1.0,
            font_weight=float(total_chars),  # 字符数作为权重
        )

    def _parse_image_block(
        self, block: dict, page_no: int, block_no: int, block_id: int
    ) -> Optional[Block]:
        """
        解析图片块

        Args:
            block: PyMuPDF的block字典
            page_no: 页码
            block_no: PyMuPDF的block编号
            block_id: 自定义block ID

        Returns:
            Block对象或None
        """
        bbox = block["bbox"]

        # 检查图片是否有意义的尺寸
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if width < 10 or height < 10:
            logger.debug(f"Skipping small image block {block_id}: {width}x{height}")
            return None

        block_id_str = f"p{page_no}_img_{block_id}"

        return Block(
            id=block_id_str,
            text="[IMAGE]",
            raw_text="[IMAGE]",
            bbox=BBox(*bbox),
            font_size=0,
            font_name="image",
            font_sizes=[],
            font_names=[],
            source_block_no=block_no,
            type_candidate=BlockType.IMAGE,
            type_final=BlockType.IMAGE,
            classification_reasons=["Detected as image block"],
            zone=None,
            column=None,
            lines_count=0,
            char_count=0,
            is_bold=False,
            confidence=1.0,
            font_weight=0.0,
        )

    def filter_blocks(self, blocks: List[Block], min_chars: int = 3) -> List[Block]:
        """
        过滤过小的文本块

        Args:
            blocks: Block列表
            min_chars: 最小字符数

        Returns:
            过滤后的Block列表
        """
        filtered = [
            block
            for block in blocks
            if block.char_count >= min_chars or block.type_final == BlockType.IMAGE
        ]
        logger.debug(f"Filtered blocks: {len(blocks)} -> {len(filtered)}")
        return filtered
