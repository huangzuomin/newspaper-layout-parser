"""
指标计算模块
Metrics Calculator - 计算block/article/column/zone指标
"""

from typing import Dict, List, Any, Tuple
from collections import Counter, defaultdict
import logging

logger = logging.getLogger("parser_auditor")


class MetricsCalculator:
    """指标计算器"""

    def __init__(self, parsed_data: Dict[str, Any]):
        """
        初始化指标计算器

        Args:
            parsed_data: parser输出的structured.json数据
        """
        self.data = parsed_data
        self.blocks = parsed_data.get('blocks', [])
        self.articles = parsed_data.get('articles', [])
        self.page_width = parsed_data.get('width', 0)
        self.page_height = parsed_data.get('height', 0)
        self.font_profile = parsed_data.get('font_profile', {})

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """
        计算所有指标

        Returns:
            包含所有指标的字典
        """
        metrics = {}

        # 1. Block级别指标
        metrics['blocks'] = self._calculate_block_metrics()

        # 2. Article级别指标
        metrics['articles'] = self._calculate_article_metrics()

        # 3. Column级别指标
        metrics['columns'] = self._calculate_column_metrics()

        # 4. Zone级别指标
        metrics['zones'] = self._calculate_zone_metrics()

        # 5. 全局指标
        metrics['global'] = self._calculate_global_metrics()

        return metrics

    def _calculate_block_metrics(self) -> Dict[str, Any]:
        """计算Block级别指标"""
        blocks = self.blocks

        # 基本统计
        type_counts = Counter(b.get('type_final', 'unknown') for b in blocks)
        zone_counts = Counter(b.get('zone', 'unknown') for b in blocks)

        # 字体大小统计
        font_sizes = [b.get('font_size', 0) for b in blocks if b.get('font_size', 0) > 0]
        font_size_stats = self._calculate_stats(font_sizes)

        # 字符数统计
        char_counts = [b.get('char_count', 0) for b in blocks]
        char_count_stats = self._calculate_stats(char_counts)

        # 分类一致性
        classification_consistency = self._calculate_classification_consistency(blocks)

        return {
            'total': len(blocks),
            'type_distribution': dict(type_counts),
            'zone_distribution': dict(zone_counts),
            'font_size_stats': font_size_stats,
            'char_count_stats': char_count_stats,
            'classification_consistency': classification_consistency,
        }

    def _calculate_article_metrics(self) -> Dict[str, Any]:
        """计算Article级别指标"""
        articles = self.articles

        # 基本统计
        total_articles = len(articles)

        # Headline覆盖率
        articles_with_headline = sum(1 for a in articles if a.get('headline_block_id'))
        headline_coverage = articles_with_headline / total_articles if total_articles > 0 else 0

        # Body blocks统计
        body_counts = [len(a.get('body_block_ids', [])) for a in articles]
        body_stats = self._calculate_stats(body_counts)

        # Captions统计
        caption_counts = [len(a.get('caption_block_ids', [])) for a in articles]

        # 按zone统计
        zone_article_counts = Counter(a.get('zone', 'unknown') for a in articles)

        # 低置信度文章
        low_confidence_articles = sum(1 for a in articles if len(a.get('body_block_ids', [])) <= 1)

        return {
            'total': total_articles,
            'headline_coverage': headline_coverage,
            'body_stats': body_stats,
            'caption_stats': self._calculate_stats(caption_counts),
            'zone_distribution': dict(zone_article_counts),
            'low_confidence_count': low_confidence_articles,
            'low_confidence_ratio': low_confidence_articles / total_articles if total_articles > 0 else 0,
        }

    def _calculate_column_metrics(self) -> Dict[str, Any]:
        """计算Column级别指标"""
        # 按column统计
        column_blocks = defaultdict(list)
        for b in self.blocks:
            col = b.get('column')
            if col is not None:
                column_blocks[col].append(b)

        total_columns = len(column_blocks)

        # 只考虑正文blocks的column宽度
        column_widths = {}
        for col, blocks in column_blocks.items():
            text_blocks = [b for b in blocks
                          if b.get('type_final') in ['body', 'subheadline']
                          and b.get('char_count', 0) >= 30]

            if text_blocks:
                x_coords = [b['bbox'][0] for b in text_blocks]
                min_x = min(x_coords)
                max_x = max([b['bbox'][2] for b in text_blocks])
                width = max_x - min_x
                width_pct = width / self.page_width * 100 if self.page_width > 0 else 0
                column_widths[col] = {
                    'width': width,
                    'width_pct': width_pct,
                    'text_block_count': len(text_blocks),
                    'total_block_count': len(blocks),
                }

        # 宽度统计
        widths = [v['width_pct'] for v in column_widths.values()]
        width_stats = self._calculate_stats(widths)

        # 检测异常窄栏和宽栏
        narrow_columns = sum(1 for v in column_widths.values() if v['width_pct'] < 8)
        wide_columns = sum(1 for v in column_widths.values() if v['width_pct'] > 70)

        return {
            'total': total_columns,
            'width_stats': width_stats,
            'column_details': column_widths,
            'narrow_column_count': narrow_columns,
            'wide_column_count': wide_columns,
            'avg_blocks_per_column': sum(len(v) for v in column_blocks.values()) / total_columns if total_columns > 0 else 0,
        }

    def _calculate_zone_metrics(self) -> Dict[str, Any]:
        """计算Zone级别指标"""
        # 按zone统计blocks
        zone_blocks = defaultdict(list)
        for b in self.blocks:
            zone = b.get('zone', 'unknown')
            zone_blocks[zone].append(b)

        zone_metrics = {}
        for zone, blocks in zone_blocks.items():
            # 每个zone的block类型分布
            type_counts = Counter(b.get('type_final', 'unknown') for b in blocks)

            # 每个zone的column分布
            col_counts = Counter(b.get('column') for b in blocks if b.get('column') is not None)

            zone_metrics[zone] = {
                'block_count': len(blocks),
                'type_distribution': dict(type_counts),
                'column_count': len(col_counts),
                'column_distribution': dict(col_counts),
            }

        return zone_metrics

    def _calculate_global_metrics(self) -> Dict[str, Any]:
        """计算全局指标"""
        blocks = self.blocks
        articles = self.articles
        data = self.data

        # 页面覆盖率
        page_coverage = self._calculate_page_coverage(blocks)

        # 字体层级清晰度
        font_clarity = self._calculate_font_clarity()

        # 阅读顺序完整性
        reading_order_completeness = len(data.get('block_reading_order', [])) / len(blocks) if blocks else 0

        return {
            'page_coverage': page_coverage,
            'font_clarity': font_clarity,
            'reading_order_completeness': reading_order_completeness,
        }

    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """计算统计数据"""
        if not values:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'median': 0,
            }

        sorted_vals = sorted(values)
        n = len(values)

        return {
            'count': n,
            'min': round(min(values), 2),
            'max': round(max(values), 2),
            'avg': round(sum(values) / n, 2),
            'median': round(sorted_vals[n // 2], 2),
        }

    def _calculate_classification_consistency(self, blocks: List[Dict]) -> Dict[str, float]:
        """计算分类一致性"""
        # 统计candidate和final一致的blocks
        consistent = sum(1 for b in blocks if b.get('type_candidate') == b.get('type_final'))
        total = len(blocks)

        return {
            'consistent_count': consistent,
            'total': total,
            'consistency_ratio': consistent / total if total > 0 else 0,
        }

    def _calculate_page_coverage(self, blocks: List[Dict]) -> Dict[str, Any]:
        """计算页面覆盖率"""
        if not blocks:
            return {'ratio': 0, 'covered_area': 0, 'total_area': 0}

        # 计算所有blocks的并集面积（简化计算）
        total_area = 0
        covered_area = 0

        for b in blocks:
            bbox = b.get('bbox', [])
            if len(bbox) >= 4:
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                block_area = width * height
                covered_area += block_area

        total_area = self.page_width * self.page_height

        return {
            'ratio': covered_area / total_area if total_area > 0 else 0,
            'covered_area': covered_area,
            'total_area': total_area,
        }

    def _calculate_font_clarity(self) -> Dict[str, Any]:
        """计算字体层级清晰度"""
        font_profile = self.font_profile
        method = font_profile.get('method', 'unknown')

        if method == 'frequency':
            # 检查是否有明确的层级区分
            headline = font_profile.get('headline')
            body = font_profile.get('body')

            if headline and body:
                headline_avg = headline[1] if isinstance(headline, tuple) and len(headline) > 1 else headline
                body_avg = body[1] if isinstance(body, tuple) and len(body) > 1 else body

                if isinstance(headline_avg, (int, float)) and isinstance(body_avg, (int, float)):
                    ratio = headline_avg / body_avg if body_avg > 0 else 1
                    return {
                        'method': method,
                        'headline_to_body_ratio': round(ratio, 2),
                        'clarity': 'good' if ratio >= 1.3 else 'poor',
                    }

        return {
            'method': method,
            'clarity': 'unknown',
        }
