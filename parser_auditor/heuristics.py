"""
启发式检查模块
Heuristics Checker - 实现结构合理性检查规则
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("parser_auditor")


class HeuristicsChecker:
    """启发式检查器"""

    def __init__(self, parsed_data: Dict[str, Any]):
        """
        初始化检查器

        Args:
            parsed_data: parser输出的structured.json数据
        """
        self.data = parsed_data
        self.blocks = parsed_data.get('blocks', [])
        self.articles = parsed_data.get('articles', [])
        self.page_width = parsed_data.get('width', 0)
        self.page_height = parsed_data.get('height', 0)

    def check_all(self) -> List[Dict[str, Any]]:
        """
        执行所有检查

        Returns:
            检查结果列表，每个结果包含issue, severity, reason
        """
        issues = []

        # 1. Block级别检查
        issues.extend(self._check_blocks())

        # 2. Article级别检查
        issues.extend(self._check_articles())

        # 3. Column级别检查
        issues.extend(self._check_columns())

        # 4. Zone级别检查
        issues.extend(self._check_zones())

        # 5. 全局检查
        issues.extend(self._check_global())

        return issues

    def _check_blocks(self) -> List[Dict[str, Any]]:
        """Block级别检查"""
        issues = []

        # 检查1: 过大或过小的blocks
        for b in self.blocks:
            char_count = b.get('char_count', 0)
            font_size = b.get('font_size', 0)

            # 字符数异常
            if char_count == 0 and b.get('type_final') != 'image':
                issues.append({
                    'type': 'empty_block',
                    'severity': 'low',
                    'block_id': b.get('id'),
                    'reason': f'Block {b.get("id")} has no characters but type is {b.get("type_final")}',
                })

            # 字号异常
            if font_size > 100 or font_size < 5:
                issues.append({
                    'type': 'abnormal_font_size',
                    'severity': 'medium',
                    'block_id': b.get('id'),
                    'reason': f'Block {b.get("id")} has abnormal font size: {font_size}pt',
                })

        return issues

    def _check_articles(self) -> List[Dict[str, Any]]:
        """Article级别检查"""
        issues = []

        for article in self.articles:
            article_id = article.get('id')
            headline_id = article.get('headline_block_id')
            body_ids = article.get('body_block_ids', [])

            # 检查1: 缺少headline
            if not headline_id:
                issues.append({
                    'type': 'missing_headline',
                    'severity': 'high',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has no headline',
                })

            # 检查2: Body blocks过少
            if len(body_ids) == 0:
                issues.append({
                    'type': 'no_body_blocks',
                    'severity': 'critical',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has no body blocks',
                })
            elif len(body_ids) <= 1:
                issues.append({
                    'type': 'too_few_body_blocks',
                    'severity': 'medium',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has only {len(body_ids)} body block(s)',
                })

            # 检查3: 单个article占用过多blocks
            if len(body_ids) > 50:
                issues.append({
                    'type': 'oversized_article',
                    'severity': 'low',
                    'article_id': article_id,
                    'reason': f'Article {article_id} has {len(body_ids)} body blocks, possibly too many',
                })

        return issues

    def _check_columns(self) -> List[Dict[str, Any]]:
        """Column级别检查"""
        issues = []

        # 统计column信息
        column_blocks = defaultdict(list)
        for b in self.blocks:
            col = b.get('column')
            if col is not None:
                column_blocks[col].append(b)

        # 检查1: 栏数异常
        total_columns = len(column_blocks)
        if total_columns == 0:
            issues.append({
                'type': 'no_columns',
                'severity': 'critical',
                'reason': 'No columns detected',
            })
        elif total_columns > 15:
            issues.append({
                'type': 'too_many_columns',
                'severity': 'high',
                'reason': f'Too many columns detected: {total_columns}',
            })

        # 检查2: 栏宽异常
        for col, blocks in column_blocks.items():
            # 只考虑正文blocks
            text_blocks = [b for b in blocks
                          if b.get('type_final') in ['body', 'subheadline']
                          and b.get('char_count', 0) >= 30]

            if text_blocks:
                x_coords = [b['bbox'][0] for b in text_blocks]
                min_x = min(x_coords)
                max_x = max([b['bbox'][2] for b in text_blocks])
                width = max_x - min_x
                width_pct = width / self.page_width * 100 if self.page_width > 0 else 0

                # 窄栏
                if width_pct < 5:
                    issues.append({
                        'type': 'narrow_column',
                        'severity': 'medium',
                        'column_id': col,
                        'reason': f'Column {col} is too narrow: {width_pct:.1f}% of page width',
                    })

                # 宽栏
                if width_pct > 90:
                    issues.append({
                        'type': 'wide_column',
                        'severity': 'low',
                        'column_id': col,
                        'reason': f'Column {col} is very wide: {width_pct:.1f}% of page width',
                    })

        return issues

    def _check_zones(self) -> List[Dict[str, Any]]:
        """Zone级别检查"""
        issues = []

        # 统计zone信息
        zone_blocks = defaultdict(list)
        for b in self.blocks:
            zone = b.get('zone', 'unknown')
            zone_blocks[zone].append(b)

        # 检查每个zone
        for zone, blocks in zone_blocks.items():
            # 检查headline zones
            if 'headline' in zone.lower():
                headlines = [b for b in blocks if b.get('type_final') == 'headline']
                if len(headlines) == 0:
                    issues.append({
                        'type': 'zone_without_headline',
                        'severity': 'medium',
                        'zone': zone,
                        'reason': f'Zone {zone} has no headline',
                    })

            # 检查zone的blocks数量
            if len(blocks) > 50:
                issues.append({
                    'type': 'overpopulated_zone',
                    'severity': 'low',
                    'zone': zone,
                    'reason': f'Zone {zone} has {len(blocks)} blocks, possibly too many',
                })

        return issues

    def _check_global(self) -> List[Dict[str, Any]]:
        """全局检查"""
        issues = []

        blocks = self.blocks
        articles = self.articles

        # 检查1: 总blocks数异常
        if len(blocks) < 10:
            issues.append({
                'type': 'too_few_blocks',
                'severity': 'high',
                'reason': f'Only {len(blocks)} blocks detected, possibly extraction failed',
            })

        # 检查2: 总articles数异常
        if len(articles) < 2:
            issues.append({
                'type': 'too_few_articles',
                'severity': 'medium',
                'reason': f'Only {len(articles)} articles detected',
            })

        # 检查3: section_label vs headline比例
        section_labels = [b for b in blocks if b.get('type_final') == 'section_label']
        headlines = [b for b in blocks if b.get('type_final') == 'headline']

        if len(section_labels) > 0 and len(headlines) > 0:
            if len(section_labels) >= len(headlines):
                issues.append({
                    'type': 'label_overfire',
                    'severity': 'medium',
                    'reason': f'Section labels ({len(section_labels)}) >= headlines ({len(headlines)})',
                })

        # 检查4: 类型分布异常
        type_counts = defaultdict(int)
        for b in blocks:
            t = b.get('type_final', 'unknown')
            type_counts[t] += 1

        if type_counts.get('headline', 0) == 0:
            issues.append({
                'type': 'no_headlines',
                'severity': 'critical',
                'reason': 'No headlines detected in page',
            })

        if type_counts.get('body', 0) == 0:
            issues.append({
                'type': 'no_body_blocks',
                'severity': 'critical',
                'reason': 'No body blocks detected in page',
            })

        return issues
