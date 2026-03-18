"""
调试报告工具
Debug Report Generator - 生成详细的诊断报告
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict


class DebugReporter:
    """调试报告生成器"""

    def __init__(self, result: Dict[str, Any], page_width: float, page_height: float):
        """
        初始化报告生成器

        Args:
            result: 解析结果
            page_width: 页面宽度
            page_height: 页面高度
        """
        self.result = result
        self.page_width = page_width
        self.page_height = page_height
        self.blocks = result.get('blocks', [])
        self.articles = result.get('articles', [])
        self.font_profile = result.get('font_profile', {})

        # 异常列表
        self.anomalies = []

    def generate_report(self, output_path: str):
        """
        生成完整的调试报告

        Args:
            output_path: 输出文件路径
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("报纸PDF解析 - 调试诊断报告")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 1. 基本统计
        report_lines.extend(self._basic_stats())

        # 2. Headline分析
        report_lines.extend(self._analyze_headlines())

        # 3. Section Label分析
        report_lines.extend(self._analyze_section_labels())

        # 4. Column分析
        report_lines.extend(self._analyze_columns())

        # 5. Article分析
        report_lines.extend(self._analyze_articles())

        # 6. Zone分布
        report_lines.extend(self._analyze_zones())

        # 7. 异常汇总
        report_lines.extend(self._summarize_anomalies())

        # 8. 验收指标
        report_lines.extend(self._acceptance_metrics())

        # 写入文件
        report_text = "\n".join(report_lines)
        Path(output_path).write_text(report_text, encoding='utf-8')

        print(f"Debug report saved to: {output_path}")
        # 不在控制台打印，避免Windows GBK编码问题

        return report_text

    def _basic_stats(self) -> List[str]:
        """基本统计信息"""
        lines = []
        lines.append("-" * 80)
        lines.append("1. 基本统计信息")
        lines.append("-" * 80)

        lines.append(f"页面尺寸: {self.page_width:.0f} x {self.page_height:.0f} points")
        lines.append(f"总Blocks: {len(self.blocks)}")
        lines.append(f"总Articles: {len(self.articles)}")
        lines.append(f"字体分析方法: {self.font_profile.get('method', 'unknown')}")
        lines.append("")

        # Block类型分布
        type_counts = Counter(b.get('type_final', 'unknown') for b in self.blocks)
        lines.append("Block类型分布:")
        for block_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {block_type}: {count}")
        lines.append("")

        return lines

    def _analyze_headlines(self) -> List[str]:
        """Headline分析"""
        lines = []
        lines.append("-" * 80)
        lines.append("2. Headline分析")
        lines.append("-" * 80)

        headlines = [b for b in self.blocks if b.get('type_final') == 'headline']

        lines.append(f"识别到的Headline数量: {len(headlines)}")
        lines.append("")

        if headlines:
            lines.append("Headline列表:")
            for i, h in enumerate(headlines, 1):
                lines.append(f"  {i}. [{h['id']}] Zone: {h.get('zone', 'N/A')}")
                lines.append(f"     文本: {h['text'][:60]}..." if len(h['text']) > 60 else f"     文本: {h['text']}")
                lines.append(f"     字号: {h['font_size']:.2f}pt, 字数: {h['char_count']}, 行数: {h['lines_count']}")
                lines.append(f"     位置: ({h['bbox'][0]:.1f}, {h['bbox'][1]:.1f})")
                lines.append(f"     分类理由: {'; '.join(h.get('classification_reasons', []))}")
                lines.append("")

            # 检查right_zone是否有headline
            right_headlines = [h for h in headlines if h.get('zone') == 'right_zone']
            if not right_headlines:
                lines.append("[WARNING]  警告: right_zone没有识别到任何headline！")
                self.anomalies.append({
                    'type': 'missing_right_zone_headline',
                    'severity': 'high',
                    'description': 'right_zone缺少headline识别'
                })
            else:
                lines.append(f"[OK] right_zone有{len(right_headlines)}个headline")
        else:
            lines.append("[ERROR] 未识别到任何headline！")
            self.anomalies.append({
                'type': 'no_headlines',
                'severity': 'critical',
                'description': '未识别到任何headline'
            })

        lines.append("")
        return lines

    def _analyze_section_labels(self) -> List[str]:
        """Section Label分析"""
        lines = []
        lines.append("-" * 80)
        lines.append("3. Section Label分析")
        lines.append("-" * 80)

        section_labels = [b for b in self.blocks if b.get('type_final') == 'section_label']

        lines.append(f"识别到的Section Label数量: {len(section_labels)}")
        lines.append("")

        headlines = [b for b in self.blocks if b.get('type_final') == 'headline']

        # 检查label_overfire
        if len(section_labels) >= len(headlines):
            lines.append("[WARNING]  警告: section_label数量 >= headline数量")
            self.anomalies.append({
                'type': 'label_overfire',
                'severity': 'medium',
                'description': f'section_label({len(section_labels)}) >= headline({len(headlines)})'
            })

        if section_labels:
            lines.append("Section Label列表:")
            for i, sl in enumerate(section_labels, 1):
                lines.append(f"  {i}. [{sl['id']}] Zone: {sl.get('zone', 'N/A')}")
                lines.append(f'     文本: "{sl["text"]}"')
                lines.append(f"     字号: {sl['font_size']:.2f}pt, 字数: {sl['char_count']}, 行数: {sl['lines_count']}")
                lines.append(f"     位置: ({sl['bbox'][0]:.1f}, {sl['bbox'][1]:.1f})")
                lines.append(f"     分类理由: {'; '.join(sl.get('classification_reasons', []))}")

                # 检查是否可能是误判的headline
                if sl['font_size'] > 14.0 and sl['char_count'] < 15:
                    lines.append(f"     [WARNING]  可能是误判: 大字号({sl['font_size']:.1f}pt)短文本")
                    self.anomalies.append({
                        'type': 'possible_headline_misclassified',
                        'severity': 'medium',
                        'block_id': sl['id'],
                        'description': f"Block {sl['id']}: 大字号({sl['font_size']:.1f}pt)短文本被判定为section_label"
                    })
                lines.append("")

        lines.append("")
        return lines

    def _analyze_columns(self) -> List[str]:
        """Column分析"""
        lines = []
        lines.append("-" * 80)
        lines.append("4. Column分析")
        lines.append("-" * 80)

        # 统计column信息
        column_info = defaultdict(lambda: {'text_blocks': [], 'all_blocks': [], 'x_coords': []})

        for b in self.blocks:
            col = b.get('column')
            if col is not None:
                column_info[col]['all_blocks'].append(b)
                # 只统计正文blocks (body, 字符数>=30)
                if b.get('type_final') in ['body', 'subheadline'] and b.get('char_count', 0) >= 30:
                    column_info[col]['text_blocks'].append(b)
                    column_info[col]['x_coords'].append(b['bbox'][0])

        # 计算栏数
        total_columns = len(column_info)
        lines.append(f"总栏数: {total_columns}")
        lines.append("")

        # 检查abnormal_columns
        if total_columns > 10:
            lines.append(f"[WARNING]  警告: 栏数({total_columns})超过10，可能存在异常")
            self.anomalies.append({
                'type': 'abnormal_columns',
                'severity': 'high',
                'description': f'栏数({total_columns})超过10'
            })

        # 输出每栏的详细信息
        lines.append("各栏详细信息:")
        for col in sorted(column_info.keys()):
            info = column_info[col]
            text_count = len(info['text_blocks'])
            all_count = len(info['all_blocks'])

            if info['x_coords']:
                min_x = min(info['x_coords'])
                max_x = max([b['bbox'][2] for b in info['text_blocks']])
                width = max_x - min_x
                width_pct = width / self.page_width * 100
            else:
                width = 0
                width_pct = 0

            lines.append(f"  Column {col}: {text_count}个正文blocks, {all_count}个总blocks")
            lines.append(f"    宽度: {width:.1f}pt ({width_pct:.1f}% of page width)")

            # 检查窄栏
            if width_pct < 8:
                lines.append(f"    [WARNING]  窄栏警告: 宽度仅{width_pct:.1f}%")
                self.anomalies.append({
                    'type': 'narrow_column',
                    'severity': 'low',
                    'column_id': col,
                    'description': f'Column {col}宽度仅{width_pct:.1f}%'
                })

        lines.append("")
        return lines

    def _analyze_articles(self) -> List[str]:
        """Article分析"""
        lines = []
        lines.append("-" * 80)
        lines.append("5. Article分析")
        lines.append("-" * 80)

        lines.append(f"识别到的Article数量: {len(self.articles)}")
        lines.append("")

        # 统计异常article
        no_headline_articles = []
        low_confidence_articles = []

        for i, article in enumerate(self.articles, 1):
            headline_id = article.get('headline_block_id')
            body_count = len(article.get('body_block_ids', []))
            zone = article.get('zone')

            lines.append(f"{i}. Article {article['id']}")
            lines.append(f"   Zone: {zone}")
            lines.append(f"   Headline: {headline_id if headline_id else '无'}")
            lines.append(f"   Body blocks: {body_count}")
            lines.append(f"   Captions: {len(article.get('caption_block_ids', []))}")

            # 检查no headline
            if not headline_id:
                lines.append(f"   [WARNING]  缺少headline")
                no_headline_articles.append(article['id'])
                self.anomalies.append({
                    'type': 'missing_headline',
                    'severity': 'medium',
                    'article_id': article['id'],
                    'description': f"Article {article['id']}缺少headline"
                })

            # 检查low confidence
            if body_count <= 1:
                lines.append(f"   [WARNING]  低置信度: 正文blocks仅{body_count}个")
                low_confidence_articles.append(article['id'])
                self.anomalies.append({
                    'type': 'low_confidence',
                    'severity': 'low',
                    'article_id': article['id'],
                    'description': f"Article {article['id']}正文blocks仅{body_count}个"
                })

            lines.append("")

        # 汇总
        if no_headline_articles:
            lines.append(f"[WARNING]  {len(no_headline_articles)}篇文章缺少headline: {', '.join(no_headline_articles)}")
            lines.append("")

        if low_confidence_articles:
            lines.append(f"[WARNING]  {len(low_confidence_articles)}篇文章低置信度: {', '.join(low_confidence_articles)}")
            lines.append("")

        return lines

    def _analyze_zones(self) -> List[str]:
        """Zone分布分析"""
        lines = []
        lines.append("-" * 80)
        lines.append("6. Zone分布")
        lines.append("-" * 80)

        zone_blocks = defaultdict(list)
        for b in self.blocks:
            zone = b.get('zone', 'unknown')
            zone_blocks[zone].append(b)

        lines.append("各Zone的Block分布:")
        for zone in sorted(zone_blocks.keys()):
            blocks = zone_blocks[zone]
            type_counts = Counter(b.get('type_final', 'unknown') for b in blocks)
            lines.append(f"  {zone}: {len(blocks)} blocks")
            lines.append(f"    类型分布: {dict(type_counts)}")

        lines.append("")
        return lines

    def _summarize_anomalies(self) -> List[str]:
        """汇总异常"""
        lines = []
        lines.append("-" * 80)
        lines.append("7. 异常汇总")
        lines.append("-" * 80)

        if not self.anomalies:
            lines.append("[OK] 未检测到异常")
        else:
            lines.append(f"检测到 {len(self.anomalies)} 个异常:")
            lines.append("")

            # 按严重程度分组
            by_severity = defaultdict(list)
            for anomaly in self.anomalies:
                by_severity[anomaly['severity']].append(anomaly)

            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in by_severity:
                    lines.append(f"{severity.upper()} ({len(by_severity[severity])}):")
                    for a in by_severity[severity]:
                        lines.append(f"  - [{a['type']}] {a['description']}")
                    lines.append("")

        return lines

    def _acceptance_metrics(self) -> List[str]:
        """验收指标"""
        lines = []
        lines.append("-" * 80)
        lines.append("8. 验收指标")
        lines.append("-" * 80)

        # 1. Headline识别指标
        headlines = [b for b in self.blocks if b.get('type_final') == 'headline']
        right_headlines = [h for h in headlines if h.get('zone') == 'right_zone']

        lines.append("1. Headline识别:")
        lines.append(f"   - 识别数量: {len(headlines)}个")
        lines.append(f"   - right_zone headline数量: {len(right_headlines)}个")
        lines.append(f"   - 状态: {'[OK] 通过' if len(right_headlines) > 0 else '[ERROR] 未通过'}")
        lines.append("")

        # 2. Article聚类指标
        no_headline_count = sum(1 for a in self.articles if not a.get('headline_block_id'))
        low_conf_count = sum(1 for a in self.articles if len(a.get('body_block_ids', [])) <= 1)

        lines.append("2. Article聚类:")
        lines.append(f"   - 文章数量: {len(self.articles)}篇")
        lines.append(f"   - 缺少headline的文章: {no_headline_count}篇")
        lines.append(f"   - 低置信度文章: {low_conf_count}篇")
        lines.append(f"   - 状态: {'[OK] 通过' if no_headline_count == 0 and low_conf_count == 0 else '[WARNING]  需改进'}")
        lines.append("")

        # 3. 分栏检测指标
        column_info = defaultdict(list)
        for b in self.blocks:
            col = b.get('column')
            if col is not None and b.get('type_final') in ['body', 'subheadline'] and b.get('char_count', 0) >= 30:
                column_info[col].append(b['bbox'][0])

        total_cols = len(column_info)
        narrow_cols = sum(1 for col, x_coords in column_info.items() if x_coords)

        lines.append("3. 分栏检测:")
        lines.append(f"   - 总栏数: {total_cols}个")
        lines.append(f"   - 状态: {'[OK] 通过(4-8栏)' if 4 <= total_cols <= 8 else '[WARNING]  需改进'}")
        lines.append("")

        # 4. Section Label指标
        section_labels = [b for b in self.blocks if b.get('type_final') == 'section_label']

        lines.append("4. Section Label:")
        lines.append(f"   - 识别数量: {len(section_labels)}个")
        lines.append(f"   - vs headline: {len(section_labels)} vs {len(headlines)}")
        lines.append(f"   - 状态: {'[OK] 通过' if len(section_labels) < len(headlines) else '[WARNING]  label_overfire'}")
        lines.append("")

        # 5. 总体评估
        critical = sum(1 for a in self.anomalies if a['severity'] == 'critical')
        high = sum(1 for a in self.anomalies if a['severity'] == 'high')

        lines.append("5. 总体评估:")
        if critical > 0:
            lines.append(f"   [ERROR] 验收未通过 - 存在{critical}个critical异常")
        elif high > 0:
            lines.append(f"   [WARNING]  需改进 - 存在{high}个high异常")
        else:
            lines.append("   [OK] 基本通过 - 无critical/high异常")

        lines.append("")

        return lines
