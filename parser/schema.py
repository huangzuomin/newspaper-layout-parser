"""
核心数据结构定义
Core data structures for the PDF parser
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import json


class BlockType(Enum):
    """Block类型枚举"""
    HEADLINE = "headline"
    SUBHEADLINE = "subheadline"
    BODY = "body"
    CAPTION = "caption"
    SECTION_LABEL = "section_label"
    IMAGE = "image"
    OTHER = "other"


class ZoneType(Enum):
    """区域类型枚举"""
    MASTHEAD = "masthead"
    HEADLINE_ZONE = "headline_zone"
    LEFT_ZONE = "left_zone"
    RIGHT_ZONE = "right_zone"
    BOTTOM_ZONE = "bottom_zone"


@dataclass
class BBox:
    """边界框"""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """宽度"""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """高度"""
        return self.y1 - self.y0

    @property
    def center(self) -> Tuple[float, float]:
        """中心点坐标"""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    @property
    def area(self) -> float:
        """面积"""
        return self.width * self.height

    def to_list(self) -> List[float]:
        """转换为列表格式"""
        return [self.x0, self.y0, self.x1, self.y1]

    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class Block:
    """文本块数据结构（完整版，包含所有必需字段）"""

    # 基础标识
    id: str

    # 文本内容
    text: str  # 清理后的文本
    raw_text: str  # 原始文本（保留空格、换行等）

    # 位置信息
    bbox: BBox

    # 字体信息（主字体）
    font_size: float
    font_name: str

    # 所有字体信息（用于字体分析）
    font_sizes: List[float] = field(default_factory=list)
    font_names: List[str] = field(default_factory=list)

    # 来源信息
    source_block_no: int = -1  # PyMuPDF原始block编号

    # 两阶段分类
    type_candidate: Optional[BlockType] = None  # 候选类型
    type_final: Optional[BlockType] = None  # 最终类型
    classification_reasons: List[str] = field(default_factory=list)  # 分类依据

    # 空间信息
    zone: Optional[ZoneType] = None
    column: Optional[int] = None

    # 统计信息
    lines_count: int = 0
    char_count: int = 0
    is_bold: bool = False

    # 置信度和权重
    confidence: float = 1.0
    font_weight: float = 0.0  # 字体权重（按字符数加权）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于JSON输出）"""
        return {
            "id": self.id,
            "text": self.text,
            "raw_text": self.raw_text,
            "bbox": self.bbox.to_list(),
            "font_size": self.font_size,
            "font_name": self.font_name,
            "font_sizes": self.font_sizes,
            "font_names": list(set(self.font_names)),  # 去重
            "source_block_no": self.source_block_no,
            "type_candidate": self.type_candidate.value if self.type_candidate else None,
            "type_final": self.type_final.value if self.type_final else None,
            "classification_reasons": self.classification_reasons,
            "zone": self.zone.value if self.zone else None,
            "column": self.column,
            "lines_count": self.lines_count,
            "char_count": self.char_count,
            "is_bold": self.is_bold,
            "confidence": self.confidence,
            "font_weight": self.font_weight,
        }


@dataclass
class Article:
    """文章数据结构（完整版，包含所有必需字段）"""

    # 基础标识
    id: str

    # 组成部分（block IDs）
    headline_block_id: Optional[str] = None  # 主标题
    subheadline_block_id: Optional[str] = None  # 副标题
    body_block_ids: List[str] = field(default_factory=list)  # 正文
    caption_block_ids: List[str] = field(default_factory=list)  # 图注
    image_block_ids: List[str] = field(default_factory=list)  # 图片

    # 空间信息
    zone: Optional[ZoneType] = None

    # 聚类质量指标
    confidence: float = 1.0
    match_reasons: List[str] = field(default_factory=list)  # 匹配原因

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于JSON输出）"""
        return {
            "id": self.id,
            "headline_block_id": self.headline_block_id,
            "subheadline_block_id": self.subheadline_block_id,
            "body_block_ids": self.body_block_ids,
            "caption_block_ids": self.caption_block_ids,
            "image_block_ids": self.image_block_ids,
            "zone": self.zone.value if self.zone else None,
            "confidence": self.confidence,
            "match_reasons": self.match_reasons,
        }


@dataclass
class PageResult:
    """单页解析结果"""

    page_no: int
    width: float
    height: float

    # Blocks和Articles
    blocks: List[Block]
    articles: List[Article]

    # 阅读顺序（里程碑3实现）
    block_reading_order: List[str] = field(default_factory=list)
    article_reading_order: List[str] = field(default_factory=list)

    # 字体配置（里程碑2实现）
    font_profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于JSON输出）"""
        return {
            "page_no": self.page_no,
            "width": self.width,
            "height": self.height,
            "blocks": [block.to_dict() for block in self.blocks],
            "articles": [article.to_dict() for article in self.articles],
            "block_reading_order": self.block_reading_order,
            "article_reading_order": self.article_reading_order,
            "font_profile": self.font_profile,
        }


# 辅助函数
def default_factory_list() -> List:
    """默认工厂函数：返回空列表"""
    return []


def default_factory_dict() -> Dict:
    """默认工厂函数：返回空字典"""
    return {}
