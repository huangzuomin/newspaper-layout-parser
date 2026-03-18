"""
报告生成模块
Report Generator - 生成最终报告（包括score、issues、suggestions）
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger("parser_auditor")


class ReportGenerator:
    """报告生成器"""

    def __init__(self, metrics: Dict[str, Any], issues: List[Dict[str, Any]], anomalies: Dict[str, List[Dict[str, Any]]]):
        """
        初始化报告生成器

        Args:
            metrics: 指标计算结果
            issues: 启发式检查发现的问题
            anomalies: 异常检测结果
        """
        self.metrics = metrics
        self.issues = issues
        self.anomalies = anomalies

    def generate_report(self) -> Dict[str, Any]:
        """
        生成完整报告

        Returns:
            包含score, confidence, metrics, issues, suggestions的字典
        """
        # 计算总分
        score, score_breakdown = self._calculate_score()

        # 确定置信度
        confidence = self._determine_confidence(score, self.anomalies)

        # 汇总问题和异常
        all_issues = self._summarize_issues()

        # 生成建议
        suggestions = self._generate_suggestions(score_breakdown, self.anomalies)

        return {
            'score': score,
            'score_breakdown': score_breakdown,
            'confidence': confidence,
            'metrics': self.metrics,
            'issues': all_issues,
            'suggestions': suggestions,
        }

    def _calculate_score(self) -> Tuple[int, Dict[str, int]]:
        """
        计算总分（0-100）

        Returns:
            (总分, 分数细项)
        """
        breakdown = {}

        # 1. Block质量分 (25分)
        block_score = self._calculate_block_score()
        breakdown['block_quality'] = block_score

        # 2. Article质量分 (35分)
        article_score = self._calculate_article_score()
        breakdown['article_quality'] = article_score

        # 3. Column质量分 (20分)
        column_score = self._calculate_column_score()
        breakdown['column_quality'] = column_score

        # 4. Zone质量分 (10分)
        zone_score = self._calculate_zone_score()
        breakdown['zone_quality'] = zone_score

        # 5. 全局质量分 (10分)
        global_score = self._calculate_global_score()
        breakdown['global_quality'] = global_score

        total_score = sum(breakdown.values())

        return total_score, breakdown

    def _calculate_block_score(self) -> int:
        """计算Block质量分 (25分)"""
        score = 25
        metrics = self.metrics.get('blocks', {})

        # 扣分项
        # 类型分布异常
        type_dist = metrics.get('type_distribution', {})
        if type_dist.get('headline', 0) == 0:
            score -= 10  # 没有headline
        if type_dist.get('body', 0) == 0:
            score -= 10  # 没有body

        # 分类一致性
        consistency = metrics.get('classification_consistency', {})
        consistency_ratio = consistency.get('consistency_ratio', 1.0)
        if consistency_ratio < 0.8:
            score -= 5  # 分类一致性低

        return max(0, score)

    def _calculate_article_score(self) -> int:
        """计算Article质量分 (35分)"""
        score = 35
        metrics = self.metrics.get('articles', {})

        # 扣分项
        # Headline覆盖率
        headline_coverage = metrics.get('headline_coverage', 1.0)
        if headline_coverage < 0.8:
            score -= int((1 - headline_coverage) * 15)  # headline不足

        # 低置信度文章比例
        low_conf_ratio = metrics.get('low_confidence_ratio', 0)
        score -= int(low_conf_ratio * 10)  # 低置信度文章

        # Body统计
        body_stats = metrics.get('body_stats', {})
        avg_body = body_stats.get('avg', 0)

        if avg_body < 3:
            score -= 10  # 平均body数量太少

        return max(0, score)

    def _calculate_column_score(self) -> int:
        """计算Column质量分 (20分)"""
        score = 20
        metrics = self.metrics.get('columns', {})

        # 扣分项
        total_columns = metrics.get('total', 0)

        # 栏数异常
        if total_columns == 0:
            score -= 20  # 没有分栏
        elif total_columns < 2:
            score -= 10  # 栏数太少
        elif total_columns > 15:
            score -= 10  # 栏数太多
        elif total_columns < 4 or total_columns > 10:
            score -= 5  # 栏数不在理想范围

        # 宽度统计
        width_stats = metrics.get('width_stats', {})
        avg_width = width_stats.get('avg', 50)

        if avg_width > 80:
            score -= 5  # 平均栏宽过大

        # 窄栏
        narrow_count = metrics.get('narrow_column_count', 0)
        score -= min(5, narrow_count * 2)  # 窄栏扣分

        return max(0, score)

    def _calculate_zone_score(self) -> int:
        """计算Zone质量分 (10分)"""
        score = 10
        metrics = self.metrics.get('zones', {})

        # 扣分项
        # 检查每个zone
        for zone, zone_metrics in metrics.items():
            # 检查headline zones
            if 'headline' in zone.lower():
                if zone_metrics.get('block_count', 0) > 0:
                    type_dist = zone_metrics.get('type_distribution', {})
                    if type_dist.get('headline', 0) == 0:
                        score -= 3  # headline zone没有headline

        return max(0, score)

    def _calculate_global_score(self) -> int:
        """计算全局质量分 (10分)"""
        score = 10
        global_metrics = self.metrics.get('global', {})

        # 扣分项
        # 阅读顺序完整性
        reading_order = global_metrics.get('reading_order_completeness', 1.0)
        if reading_order < 0.9:
            score -= 3

        # 字体清晰度
        font_clarity = global_metrics.get('font_clarity', {})
        if font_clarity.get('clarity') == 'poor':
            score -= 3

        return max(0, score)

    def _determine_confidence(self, score: int, anomalies: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        确定置信度

        Args:
            score: 总分
            anomalies: 异常字典

        Returns:
            'high', 'medium', 或 'low'
        """
        # 统计异常数量和严重程度
        total_anomalies = sum(len(v) for v in anomalies.values())

        critical_count = sum(1 for v in anomalies.values()
                           for a in v if a.get('severity') == 'critical')

        high_count = sum(1 for v in anomalies.values()
                        for a in v if a.get('severity') == 'high')

        # 基于分数和异常确定置信度
        if score >= 80 and critical_count == 0 and high_count <= 1:
            return 'high'
        elif score >= 60 and critical_count == 0:
            return 'medium'
        else:
            return 'low'

    def _summarize_issues(self) -> Dict[str, Any]:
        """汇总问题和异常"""
        summary = {
            'total_issues': len(self.issues),
            'total_anomalies': sum(len(v) for v in self.anomalies.values()),
            'by_severity': {
                'critical': [],
                'high': [],
                'medium': [],
                'low': [],
            },
        }

        # 统计issues按严重程度
        for issue in self.issues:
            severity = issue.get('severity', 'low')
            summary['by_severity'][severity].append({
                'type': issue.get('type'),
                'reason': issue.get('reason'),
            })

        # 统计anomalies按严重程度
        for category, anomaly_list in self.anomalies.items():
            for anomaly in anomaly_list:
                severity = anomaly.get('severity', 'low')
                summary['by_severity'][severity].append({
                    'category': category,
                    'type': anomaly.get('type'),
                    'reason': anomaly.get('reason'),
                })

        return summary

    def _generate_suggestions(self, score_breakdown: Dict[str, int], anomalies: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        生成改进建议

        Args:
            score_breakdown: 分数细项
            anomalies: 异常字典

        Returns:
            建议列表
        """
        suggestions = []

        # 基于分数细项生成建议
        if score_breakdown.get('block_quality', 25) < 20:
            suggestions.append("建议检查Block分类规则，可能存在分类错误")

        if score_breakdown.get('article_quality', 35) < 25:
            suggestions.append("建议检查Article聚类逻辑，可能存在聚类错误")

        if score_breakdown.get('column_quality', 20) < 15:
            suggestions.append("建议调整分栏检测参数，可能存在分栏不合理")

        # 基于异常生成建议
        all_anomalies = []
        for anomaly_list in anomalies.values():
            all_anomalies.extend(anomaly_list)

        # 按异常类型分组
        anomaly_types = {}
        for a in all_anomalies:
            t = a.get('type')
            if t not in anomaly_types:
                anomaly_types[t] = []
            anomaly_types[t].append(a)

        # 生成针对性建议
        if 'no_headlines' in anomaly_types or 'no_headlines_page' in anomaly_types:
            suggestions.append("关键问题：页面没有识别到headline，建议调整font_analyzer的headline阈值")

        if 'article_without_headline' in anomaly_types:
            suggestions.append("关键问题：部分文章缺少headline，建议检查article_builder的headline匹配逻辑")

        if 'column_crosses_zones' in anomaly_types:
            suggestions.append("关键问题：分栏跨zone，建议使用按zone分栏的模式")

        if 'too_many_columns' in anomaly_types:
            suggestions.append("分栏过多，建议提高gap_threshold_multiplier或min_column_width_ratio")

        if 'narrow_column' in anomaly_types or 'extremely_narrow_column' in anomaly_types:
            suggestions.append("存在窄栏，建议检查合并窄栏的逻辑是否正确执行")

        if 'classification_mismatch' in anomaly_types:
            mismatch_count = len(anomaly_types.get('classification_mismatch', []))
            suggestions.append(f"有{mismatch_count}个blocks的候选分类和最终分类不一致，建议检查block_classifier")

        if not suggestions:
            suggestions.append("整体质量良好，未发现明显问题")

        return suggestions
