"""
异常检测模块
Anomaly Detector - 检测column、zone、article异常
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("parser_auditor")


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, parsed_data: Dict[str, Any]):
        """
        初始化异常检测器

        Args:
            parsed_data: parser输出的structured.json数据
        """
        self.data = parsed_data
        self.blocks = parsed_data.get('blocks', [])
        self.articles = parsed_data.get('articles', [])
        self.page_width = parsed_data.get('width', 0)
        self.page_height = parsed_data.get('height', 0)

    def detect_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        检测所有异常

        Returns:
            按类别分组的异常字典
        """
        anomalies = {
            'column': [],
            'zone': [],
            'article': [],
            'block': [],
            'global': [],
        }

        # 检测column异常
        anomalies['column'] = self._detect_column_anomalies()

        # 检测zone异常
        anomalies['zone'] = self._detect_zone_anomalies()

        # 检测article异常
        anomalies['article'] = self._detect_article_anomalies()

        # 检测block异常
        anomalies['block'] = self._detect_block_anomalies()

        # 检测全局异常
        anomalies['global'] = self._detect_global_anomalies()

        return anomalies

    def _detect_column_anomalies(self) -> List[Dict[str, Any]]:
        """检测Column异常"""
        anomalies = []

        # 统计column信息
        column_blocks = defaultdict(list)
        column_x_ranges = defaultdict(list)
        column_zones = defaultdict(set)

        for b in self.blocks:
            col = b.get('column')
            if col is not None:
                column_blocks[col].append(b)
                column_x_ranges[col].append(b['bbox'][0])
                column_zones[col].add(b.get('zone', 'unknown'))

        total_columns = len(column_blocks)

        # 异常1: 栏数过多或过少
        if total_columns > 12:
            anomalies.append({
                'type': 'abnormal_column_count',
                'severity': 'high',
                'value': total_columns,
                'expected': '4-8',
                'reason': f'Too many columns: {total_columns}, expected 4-8',
            })
        elif total_columns < 2:
            anomalies.append({
                'type': 'abnormal_column_count',
                'severity': 'medium',
                'value': total_columns,
                'expected': '4-8',
                'reason': f'Too few columns: {total_columns}, expected 4-8',
            })

        # 异常2: Column跨多个zones
        for col, zones in column_zones.items():
            if len(zones) > 3:
                anomalies.append({
                    'type': 'column_crosses_zones',
                    'severity': 'high',
                    'column_id': col,
                    'zones': list(zones),
                    'reason': f'Column {col} crosses {len(zones)} zones: {list(zones)}',
                })

        # 异常3: Column宽度异常
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

                if width_pct < 5:
                    anomalies.append({
                        'type': 'extremely_narrow_column',
                        'severity': 'medium',
                        'column_id': col,
                        'width_pct': width_pct,
                        'reason': f'Column {col} is extremely narrow: {width_pct:.1f}%',
                    })

        return anomalies

    def _detect_zone_anomalies(self) -> List[Dict[str, Any]]:
        """检测Zone异常"""
        anomalies = []

        # 统计zone信息
        zone_blocks = defaultdict(list)
        zone_articles = defaultdict(list)

        for b in self.blocks:
            zone = b.get('zone', 'unknown')
            zone_blocks[zone].append(b)

        for a in self.articles:
            zone = a.get('zone', 'unknown')
            zone_articles[zone].append(a)

        # 检查每个zone
        for zone, blocks in zone_blocks.items():
            # 异常1: zone没有headline
            headlines = [b for b in blocks if b.get('type_final') == 'headline']
            articles = zone_articles.get(zone, [])

            if zone not in ['masthead', 'unknown'] and len(articles) > 0 and len(headlines) == 0:
                anomalies.append({
                    'type': 'zone_without_headline',
                    'severity': 'high',
                    'zone': zone,
                    'reason': f'Zone {zone} has {len(articles)} articles but no headline',
                })

            # 异常2: zone的blocks数量异常
            if zone in ['left_zone', 'right_zone', 'headline_zone']:
                if len(blocks) > 30:
                    anomalies.append({
                        'type': 'overpopulated_zone',
                        'severity': 'medium',
                        'zone': zone,
                        'block_count': len(blocks),
                        'reason': f'Zone {zone} has too many blocks: {len(blocks)}',
                    })
                elif len(blocks) < 3:
                    anomalies.append({
                        'type': 'underpopulated_zone',
                        'severity': 'low',
                        'zone': zone,
                        'block_count': len(blocks),
                        'reason': f'Zone {zone} has very few blocks: {len(blocks)}',
                    })

        return anomalies

    def _detect_article_anomalies(self) -> List[Dict[str, Any]]:
        """检测Article异常"""
        anomalies = []

        for article in self.articles:
            article_id = article.get('id')
            headline_id = article.get('headline_block_id')
            body_ids = article.get('body_block_ids', [])
            caption_ids = article.get('caption_block_ids', [])

            # 异常1: 缺少headline
            if not headline_id:
                anomalies.append({
                    'type': 'article_without_headline',
                    'severity': 'high',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has no headline',
                })

            # 异常2: Body blocks数量异常
            if len(body_ids) == 0:
                anomalies.append({
                    'type': 'article_without_body',
                    'severity': 'critical',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has no body blocks',
                })
            elif len(body_ids) == 1:
                anomalies.append({
                    'type': 'article_with_single_body_block',
                    'severity': 'medium',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has only 1 body block',
                })
            elif len(body_ids) > 30:
                anomalies.append({
                    'type': 'oversized_article',
                    'severity': 'low',
                    'article_id': article_id,
                    'body_count': len(body_ids),
                    'reason': f'Article {article_id} has {len(body_ids)} body blocks, possibly too many',
                })

            # 异常3: Captions多于articles
            if len(caption_ids) > len(body_ids):
                anomalies.append({
                    'type': 'more_captions_than_body',
                    'severity': 'low',
                    'article_id': article_id,
                    'caption_count': len(caption_ids),
                    'body_count': len(body_ids),
                    'reason': f'Article {article_id} has more captions ({len(caption_ids)}) than body blocks ({len(body_ids)})',
                })

        return anomalies

    def _detect_block_anomalies(self) -> List[Dict[str, Any]]:
        """检测Block异常"""
        anomalies = []

        for b in self.blocks:
            block_id = b.get('id')

            # 异常1: 分类不一致
            if b.get('type_candidate') != b.get('type_final'):
                anomalies.append({
                    'type': 'classification_mismatch',
                    'severity': 'low',
                    'block_id': block_id,
                    'candidate': b.get('type_candidate'),
                    'final': b.get('type_final'),
                    'reason': f'Block {block_id}: candidate ({b.get("type_candidate")}) != final ({b.get("type_final")})',
                })

            # 异常2: 字符数为0但类型不是image
            if b.get('char_count', 0) == 0 and b.get('type_final') != 'image':
                anomalies.append({
                    'type': 'empty_text_block',
                    'severity': 'medium',
                    'block_id': block_id,
                    'type': b.get('type_final'),
                    'reason': f'Block {block_id} has no characters but type is {b.get("type_final")}',
                })

            # 异常3: 字号异常
            font_size = b.get('font_size', 0)
            if font_size > 72:
                anomalies.append({
                    'type': 'oversized_font',
                    'severity': 'low',
                    'block_id': block_id,
                    'font_size': font_size,
                    'reason': f'Block {block_id} has very large font size: {font_size}pt',
                })
            elif font_size < 6:
                anomalies.append({
                    'type': 'undersized_font',
                    'severity': 'low',
                    'block_id': block_id,
                    'font_size': font_size,
                    'reason': f'Block {block_id} has very small font size: {font_size}pt',
                })

        return anomalies

    def _detect_global_anomalies(self) -> List[Dict[str, Any]]:
        """检测全局异常"""
        anomalies = []

        blocks = self.blocks
        articles = self.articles

        # 异常1: 缺少关键类型
        type_counts = defaultdict(int)
        for b in blocks:
            t = b.get('type_final', 'unknown')
            type_counts[t] += 1

        if type_counts.get('headline', 0) == 0:
            anomalies.append({
                'type': 'no_headlines_page',
                'severity': 'critical',
                'reason': 'Page has no headlines at all',
            })

        if type_counts.get('body', 0) == 0:
            anomalies.append({
                'type': 'no_body_page',
                'severity': 'critical',
                'reason': 'Page has no body blocks at all',
            })

        # 异常2: 文章数异常
        if len(articles) == 0:
            anomalies.append({
                'type': 'no_articles',
                'severity': 'critical',
                'reason': 'No articles detected',
            })
        elif len(articles) == 1:
            anomalies.append({
                'type': 'only_one_article',
                'severity': 'medium',
                'reason': 'Only 1 article detected, expected multiple',
            })

        # 异常3: Section label过多
        section_labels = type_counts.get('section_label', 0)
        headlines = type_counts.get('headline', 0)

        if section_labels > 0 and section_labels >= headlines:
            anomalies.append({
                'type': 'section_label_overfire',
                'severity': 'medium',
                'section_label_count': section_labels,
                'headline_count': headlines,
                'reason': f'Section labels ({section_labels}) >= headlines ({headlines})',
            })

        return anomalies
