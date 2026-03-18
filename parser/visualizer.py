"""
可视化模块
Visualizer - Generate visualization images for debugging
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List, Optional
import logging

from .schema import Block, BBox, ZoneType, Article

logger = logging.getLogger("parser")


class Visualizer:
    """可视化调试工具"""

    # 类型颜色配置
    TYPE_COLORS = {
        "headline": "#FF0000",        # 红色
        "subheadline": "#FF6600",     # 橙色
        "body": "#0066FF",            # 蓝色
        "caption": "#00CC00",         # 绿色
        "section_label": "#CC00FF",   # 紫色
        "image": "#FFCC00",           # 黄色
        "other": "#999999",           # 灰色
        None: "#000000",              # 黑色（未分类）
    }

    # Zone背景颜色配置（淡色）
    ZONE_COLORS = {
        ZoneType.MASTHEAD: "#FFE6E6",
        ZoneType.HEADLINE_ZONE: "#FFF4E6",
        ZoneType.LEFT_ZONE: "#E6F2FF",
        ZoneType.RIGHT_ZONE: "#E6FFE6",
        ZoneType.BOTTOM_ZONE: "#F9E6FF",
        None: "#FFFFFF",
    }

    def __init__(self, dpi: int = 150, figsize: tuple = (16, 22)):
        """
        初始化可视化器

        Args:
            dpi: 图像分辨率
            figsize: 图像尺寸（英寸）
        """
        self.dpi = dpi
        self.figsize = figsize

    def visualize_raw_blocks(
        self,
        blocks: List[Block],
        page_width: float,
        page_height: float,
        output_path: str,
        show_block_ids: bool = True,
        show_font_sizes: bool = True,
    ):
        """
        可视化Raw Blocks（里程碑1）

        Args:
            blocks: Block列表
            page_width: 页面宽度
            page_height: 页面高度
            output_path: 输出文件路径
            show_block_ids: 是否显示block ID
            show_font_sizes: 是否显示字体大小
        """
        logger.info(f"Generating raw blocks visualization: {output_path}")

        # 创建图像
        fig, ax = plt.subplots(1, 1, figsize=self.figsize, dpi=self.dpi)
        ax.set_xlim(0, page_width)
        ax.set_ylim(page_height, 0)  # y轴反转
        ax.set_aspect("equal")

        # 设置标题
        ax.set_title(
            f"Raw Blocks ({len(blocks)} blocks)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        # 绘制所有blocks
        for idx, block in enumerate(blocks):
            self._draw_raw_block(
                ax, block, idx, show_block_ids, show_font_sizes
            )

        # 添加统计信息
        self._add_statistics(ax, blocks, page_width, page_height)

        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
        plt.close()

        logger.info(f"Visualization saved: {output_path}")

    def _draw_raw_block(
        self,
        ax: Axes,
        block: Block,
        idx: int,
        show_id: bool,
        show_font: bool,
    ):
        """
        绘制单个原始block

        Args:
            ax: Matplotlib轴对象
            block: Block对象
            idx: 索引编号
            show_id: 是否显示ID
            show_font: 是否显示字体
        """
        bbox = block.bbox

        # 绘制bbox
        rect = patches.Rectangle(
            (bbox.x0, bbox.y0),
            bbox.width,
            bbox.height,
            linewidth=1.5,
            edgecolor="blue",
            facecolor="none",
            alpha=0.7,
        )
        ax.add_patch(rect)

        # 显示block ID和字体大小
        if show_id or show_font:
            label_parts = []
            if show_id:
                label_parts.append(f"#{idx}")
                label_parts.append(f"{block.id}")

            if show_font and block.font_size > 0:
                label_parts.append(f"{block.font_size:.1f}pt")

            label = "\n".join(label_parts)

            # 文本位置（bbox上方）
            text_y = bbox.y0 - 5
            if text_y < 0:
                text_y = bbox.y0 + 15  # 如果在顶部，显示在bbox内部

            ax.text(
                bbox.x0,
                text_y,
                label,
                fontsize=7,
                color="blue",
                verticalalignment="top",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="blue",
                    alpha=0.8,
                ),
            )

        # 在block中心显示字符数
        if bbox.width > 30 and bbox.height > 15:
            ax.text(
                bbox.center[0],
                bbox.center[1],
                f"{block.char_count}ch",
                fontsize=6,
                color="gray",
                ha="center",
                va="center",
                alpha=0.5,
            )

    def _add_statistics(
        self,
        ax: Axes,
        blocks: List[Block],
        page_width: float,
        page_height: float,
    ):
        """
        添加统计信息

        Args:
            ax: Matplotlib轴对象
            blocks: Block列表
            page_width: 页面宽度
            page_height: 页面高度
        """
        # 统计信息
        total_blocks = len(blocks)
        text_blocks = [b for b in blocks if b.char_count > 0]
        image_blocks = [b for b in blocks if b.char_count == 0]

        # 字体大小统计
        font_sizes = [b.font_size for b in text_blocks if b.font_size > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

        # 总字符数
        total_chars = sum(b.char_count for b in text_blocks)

        # 统计文本
        stats_text = f"""Statistics:
Total Blocks: {total_blocks}
Text Blocks: {len(text_blocks)}
Image Blocks: {len(image_blocks)}
Total Characters: {total_chars}
Avg Font Size: {avg_font_size:.1f}pt
Page Size: {page_width:.0f} x {page_height:.0f}"""

        # 添加到左上角
        ax.text(
            10,
            10,
            stats_text,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="wheat",
                alpha=0.8,
            ),
        )

        # 添加比例尺
        self._add_scale_bar(ax, page_width, page_height)

    def _add_scale_bar(self, ax: Axes, page_width: float, page_height: float):
        """
        添加比例尺

        Args:
            ax: Matplotlib轴对象
            page_width: 页面宽度
            page_height: 页面高度
        """
        # 比例尺长度（100点）
        scale_length = 100
        scale_x = page_width - scale_length - 20
        scale_y = page_height - 30

        # 绘制比例尺
        ax.plot(
            [scale_x, scale_x + scale_length],
            [scale_y, scale_y],
            color="black",
            linewidth=2,
        )
        ax.plot(
            [scale_x, scale_x],
            [scale_y - 5, scale_y + 5],
            color="black",
            linewidth=2,
        )
        ax.plot(
            [scale_x + scale_length, scale_x + scale_length],
            [scale_y - 5, scale_y + 5],
            color="black",
            linewidth=2,
        )

        # 添加标注
        ax.text(
            (scale_x + scale_x + scale_length) / 2,
            scale_y - 10,
            f"{scale_length}pt",
            fontsize=8,
            ha="center",
        )

    def visualize_structure(
        self,
        blocks: List[Block],
        page_width: float,
        page_height: float,
        output_path: str,
        show_zones: bool = True,
        show_columns: bool = True,
        show_block_types: bool = True,
    ):
        """
        可视化结构信息（里程碑2）

        Args:
            blocks: Block列表
            page_width: 页面宽度
            page_height: 页面高度
            output_path: 输出文件路径
            show_zones: 是否显示zone背景
            show_columns: 是否显示column分隔线
            show_block_types: 是否使用不同颜色显示block类型
        """
        logger.info(f"Generating structure visualization: {output_path}")

        # 创建图像
        fig, ax = plt.subplots(1, 1, figsize=self.figsize, dpi=self.dpi)
        ax.set_xlim(0, page_width)
        ax.set_ylim(page_height, 0)  # y轴反转
        ax.set_aspect("equal")

        # 设置标题
        ax.set_title(
            f"Structure Analysis ({len(blocks)} blocks)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        # 绘制zone背景
        if show_zones:
            self._draw_zones(ax, page_width, page_height)

        # 绘制column分隔线
        if show_columns:
            self._draw_columns(ax, blocks, page_height)

        # 绘制blocks
        for block in blocks:
            self._draw_structured_block(ax, block, show_block_types)

        # 添加统计信息
        self._add_structure_statistics(ax, blocks, page_width, page_height)

        # 添加图例
        self._add_legend(ax)

        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
        plt.close()

        logger.info(f"Structure visualization saved: {output_path}")

    def _draw_zones(self, ax: Axes, page_width: float, page_height: float):
        """绘制zone背景"""
        # Zone定义（与layout_profile.yaml中的配置一致）
        zones = [
            (ZoneType.MASTHEAD, 0, 0, page_width, page_height * 0.15),
            (ZoneType.HEADLINE_ZONE, 0, page_height * 0.15, page_width, page_height * 0.15),
            (ZoneType.LEFT_ZONE, 0, page_height * 0.30, page_width * 0.65, page_height * 0.45),
            (ZoneType.RIGHT_ZONE, page_width * 0.65, page_height * 0.30, page_width * 0.35, page_height * 0.45),
            (ZoneType.BOTTOM_ZONE, 0, page_height * 0.75, page_width, page_height * 0.25),
        ]

        for zone, x0, y0, w, h in zones:
            color = self.ZONE_COLORS.get(zone, "#F0F0F0")
            rect = patches.Rectangle(
                (x0, y0),
                w,
                h,
                linewidth=0,
                facecolor=color,
                alpha=0.3,
            )
            ax.add_patch(rect)

            # 添加zone标签
            ax.text(
                x0 + 10,
                y0 + 20,
                zone.value,
                fontsize=10,
                color="#666666",
                style="italic",
                fontweight="bold",
            )

    def _draw_columns(self, ax: Axes, blocks: List[Block], page_height: float):
        """绘制column分隔线"""
        # 收集所有column的边界
        column_boundaries = set()
        for block in blocks:
            if block.column is not None:
                column_boundaries.add(block.bbox.x0)
                column_boundaries.add(block.bbox.x1)

        # 绘制分隔线
        for x in sorted(column_boundaries):
            ax.axvline(
                x=x,
                color="#CCCCCC",
                linestyle="--",
                linewidth=1.5,
                alpha=0.7,
            )

    def _draw_structured_block(self, ax: Axes, block: Block, show_types: bool):
        """绘制单个结构化block"""
        # 确定颜色
        if show_types and block.type_candidate:
            color = self.TYPE_COLORS.get(
                block.type_candidate.value,
                "#999999"
            )
        else:
            color = "blue"

        # 绘制bbox
        rect = patches.Rectangle(
            (block.bbox.x0, block.bbox.y0),
            block.bbox.width,
            block.bbox.height,
            linewidth=2,
            edgecolor=color,
            facecolor="none",
            alpha=0.8,
        )
        ax.add_patch(rect)

        # 显示类型标签
        if block.type_candidate:
            label = block.type_candidate.value[0].upper()
            ax.text(
                block.bbox.x0 + 5,
                block.bbox.y0 + 15,
                label,
                fontsize=9,
                color=color,
                fontweight="bold",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor=color,
                    alpha=0.8,
                ),
            )

        # 显示zone信息（如果有）
        if block.zone:
            ax.text(
                block.bbox.x1 - 5,
                block.bbox.y1 - 10,
                f"{block.zone.value[0:2]}",
                fontsize=7,
                color="gray",
                ha="right",
            )

        # 显示column信息（如果有）
        if block.column is not None:
            ax.text(
                block.bbox.x1 - 5,
                block.bbox.y0 + 5,
                f"C{block.column}",
                fontsize=7,
                color="green",
                ha="right",
            )

    def _add_structure_statistics(
        self,
        ax: Axes,
        blocks: List[Block],
        page_width: float,
        page_height: float,
    ):
        """添加结构统计信息"""
        # 统计各类型blocks
        type_counts = {}
        zone_counts = {}
        column_count = len(set(b.column for b in blocks if b.column is not None))

        for block in blocks:
            if block.type_candidate:
                type_value = block.type_candidate.value
                type_counts[type_value] = type_counts.get(type_value, 0) + 1

            if block.zone:
                zone_value = block.zone.value
                zone_counts[zone_value] = zone_counts.get(zone_value, 0) + 1

        # 统计文本
        stats_lines = [
            f"Total Blocks: {len(blocks)}",
            f"Columns: {column_count}",
            "",
            "By Type:",
        ]
        for type_name, count in sorted(type_counts.items()):
            stats_lines.append(f"  {type_name}: {count}")

        stats_lines.append("")
        stats_lines.append("By Zone:")
        for zone_name, count in sorted(zone_counts.items()):
            stats_lines.append(f"  {zone_name}: {count}")

        stats_text = "\n".join(stats_lines)

        # 添加到左上角
        ax.text(
            10,
            10,
            stats_text,
            fontsize=8,
            verticalalignment="top",
            family="monospace",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="wheat",
                alpha=0.8,
            ),
        )

        # 添加比例尺
        self._add_scale_bar(ax, page_width, page_height)

    def _add_legend(self, ax: Axes):
        """添加图例"""
        legend_elements = []
        for block_type, color in self.TYPE_COLORS.items():
            if block_type:  # 跳过None
                legend_elements.append(
                    patches.Patch(
                        facecolor=color,
                        edgecolor=color,
                        label=block_type.capitalize(),
                        alpha=0.7,
                    )
                )

        ax.legend(
            handles=legend_elements,
            loc="upper right",
            fontsize=8,
            bbox_to_anchor=(1.0, 1.0),
        )

    def visualize_articles(
        self,
        blocks: List[Block],
        articles: List[Article],
        page_width: float,
        page_height: float,
        output_path: str,
        show_article_bounds: bool = True,
        show_article_connections: bool = True,
        show_reading_order: bool = True,
        block_order: List[str] = None,
        article_order: List[str] = None,
    ):
        """
        可视化文章信息（里程碑3）

        Args:
            blocks: Block列表
            articles: Article列表
            page_width: 页面宽度
            page_height: 页面高度
            output_path: 输出文件路径
            show_article_bounds: 是否显示article边界
            show_article_connections: 是否显示headline到body的连线
            show_reading_order: 是否显示阅读顺序编号
            block_order: Block级阅读顺序
            article_order: Article级阅读顺序
        """
        logger.info(f"Generating article visualization: {output_path}")

        # 创建图像
        fig, ax = plt.subplots(1, 1, figsize=self.figsize, dpi=self.dpi)
        ax.set_xlim(0, page_width)
        ax.set_ylim(page_height, 0)  # y轴反转
        ax.set_aspect("equal")

        # 设置标题
        ax.set_title(
            f"Article Analysis ({len(articles)} articles, {len(blocks)} blocks)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        # 绘制zone背景（复用结构可视化）
        self._draw_zones(ax, page_width, page_height)

        # 绘制column分隔线（复用结构可视化）
        self._draw_columns(ax, blocks, page_height)

        # 绘制article边界
        if show_article_bounds:
            self._draw_article_bounds(ax, articles, blocks)

        # 绘制blocks
        for block in blocks:
            self._draw_structured_block(ax, block, show_types=True)

        # 绘制article连接线
        if show_article_connections:
            self._draw_article_connections(ax, articles, blocks)

        # 显示阅读顺序
        if show_reading_order and block_order:
            self._draw_reading_order_numbers(ax, blocks, block_order)

        # 添加文章统计信息
        self._add_article_statistics(ax, articles, blocks, page_width, page_height)

        # 保存
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
        plt.close()

        logger.info(f"Article visualization saved: {output_path}")

    def _draw_article_bounds(self, ax: Axes, articles: List[Article], blocks: List[Block]):
        """绘制article边界（虚线框）"""
        # 创建block ID到block的映射
        block_map = {b.id: b for b in blocks}

        for article in articles:
            # 收集article中的所有blocks
            article_block_ids = [article.headline_block_id] + article.body_block_ids

            # 计算article的边界
            x0 = float('inf')
            y0 = float('inf')
            x1 = float('-inf')
            y1 = float('-inf')

            for block_id in article_block_ids:
                if block_id not in block_map:
                    continue

                block = block_map[block_id]
                bbox = block.bbox

                x0 = min(x0, bbox.x0)
                y0 = min(y0, bbox.y0)
                x1 = max(x1, bbox.x1)
                y1 = max(y1, bbox.y1)

            if x0 == float('inf'):
                continue

            # 绘制article边界（虚线框）
            rect = patches.Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                linewidth=3,
                edgecolor="purple",
                facecolor="none",
                linestyle="--",
                alpha=0.5,
            )
            ax.add_patch(rect)

            # 添加article ID标签
            ax.text(
                x0 + 10,
                y0 + 30,
                f"ARTICLE: {article.id}",
                fontsize=11,
                color="purple",
                fontweight="bold",
                bbox=dict(
                    boxstyle="round,pad=0.5",
                    facecolor="white",
                    edgecolor="purple",
                    alpha=0.9,
                ),
            )

    def _draw_article_connections(self, ax: Axes, articles: List[Article], blocks: List[Block]):
        """绘制headline到body的连接线"""
        block_map = {b.id: b for b in blocks}

        for article in articles:
            if not article.headline_block_id:
                continue

            headline = block_map.get(article.headline_block_id)
            if not headline:
                continue

            # 绘制从headline到每个body的连接线
            for body_id in article.body_block_ids[:5]:  # 限制显示前5个，避免太乱
                body = block_map.get(body_id)
                if not body:
                    continue

                # 绘制连线
                ax.plot(
                    [headline.bbox.center[0], body.bbox.center[0]],
                    [headline.bbox.y1, body.bbox.y0],
                    color="purple",
                    linestyle=":",
                    linewidth=0.8,
                    alpha=0.4,
                )

    def _draw_reading_order_numbers(self, ax: Axes, blocks: List[Block], block_order: List[str]):
        """绘制阅读顺序编号"""
        # 创建block ID到索引的映射
        block_id_to_index = {
            block_id: idx
            for idx, block_id in enumerate(block_order)
        }

        for block in blocks:
            if block.id in block_id_to_index:
                order_idx = block_id_to_index[block.id]

                # 在block右上角显示编号
                ax.text(
                    block.bbox.x1 - 5,
                    block.bbox.y0 + 5,
                    f"#{order_idx + 1}",
                    fontsize=7,
                    color="black",
                    fontweight="bold",
                    ha="right",
                    bbox=dict(
                        boxstyle="circle",
                        pad=0.3,
                        facecolor="yellow",
                        edgecolor="black",
                        alpha=0.7,
                    ),
                )

    def _add_article_statistics(
        self,
        ax: Axes,
        articles: List[Article],
        blocks: List[Block],
        page_width: float,
        page_height: float,
    ):
        """添加文章统计信息"""
        # 统计各zone的文章数
        zone_article_counts = {}
        for article in articles:
            if article.zone:
                zone = article.zone.value
                zone_article_counts[zone] = zone_article_counts.get(zone, 0) + 1

        # 统计文章组成
        total_headlines = sum(1 for a in articles if a.headline_block_id)
        total_bodies = sum(len(a.body_block_ids) for a in articles)
        total_captions = sum(len(a.caption_block_ids) for a in articles)
        total_images = sum(len(a.image_block_ids) for a in articles)

        # 统计文本
        stats_lines = [
            f"Articles: {len(articles)}",
            f"  With headline: {total_headlines}",
            f"  Without headline: {len(articles) - total_headlines}",
            "",
            f"Article blocks:",
            f"  Body blocks: {total_bodies}",
            f"  Captions: {total_captions}",
            f"  Images: {total_images}",
            "",
            "Articles by zone:",
        ]
        for zone, count in sorted(zone_article_counts.items()):
            stats_lines.append(f"  {zone}: {count}")

        stats_text = "\n".join(stats_lines)

        # 添加到左上角
        ax.text(
            10,
            10,
            stats_text,
            fontsize=8,
            verticalalignment="top",
            family="monospace",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="lightyellow",
                alpha=0.8,
            ),
        )

        # 添加比例尺
        self._add_scale_bar(ax, page_width, page_height)
