"""
优化建议引擎
Optimization Engine - 生成专业优化建议

与RiskEngine不同，OptimizationEngine提供可选的改进建议，
旨在提升版面质量，而非把关风险。
"""

from typing import List, Dict, Any
import logging

from ..models.optimization import (
    OptimizationSuggestion,
    OptimizationReport,
    OptimizationCategory,
    OptimizationPriority
)
from ..models.risk import Risk

logger = logging.getLogger("intelligent_editor")


class OptimizationEngine:
    """
    优化建议引擎

    为版面提供专业优化建议，包括：
    - 标题优化（长度、字号、位置）
    - 版面平衡（左右平衡、上下平衡）
    - 视觉层次（标题、副标题、正文的层次）
    - 可读性（分栏、字号、行距）
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化优化建议引擎

        Args:
            config: 优化规则配置
        """
        self.config = config
        self.headline_rules = config.get('headline_rules', {})
        self.layout_rules = config.get('layout_rules', {})
        self.visual_rules = config.get('visual_rules', {})

        logger.info("OptimizationEngine initialized")

    def generate_suggestions(
        self,
        structured_data: Dict[str, Any],
        metrics: Dict[str, Any],
        risks: List[Risk]
    ) -> OptimizationReport:
        """
        生成优化建议

        Args:
            structured_data: parser输出的结构化数据
            metrics: parser_auditor的质量指标
            risks: 已识别的风险

        Returns:
            OptimizationReport对象
        """
        suggestions = []

        # 1. 标题优化建议
        headline_suggestions = self._analyze_headlines(
            structured_data,
            metrics
        )
        suggestions.extend(headline_suggestions)

        # 2. 版面平衡建议
        layout_suggestions = self._analyze_layout_balance(
            structured_data,
            metrics
        )
        suggestions.extend(layout_suggestions)

        # 3. 视觉层次建议
        visual_suggestions = self._analyze_visual_hierarchy(
            structured_data,
            metrics
        )
        suggestions.extend(visual_suggestions)

        # 4. 可读性建议
        readability_suggestions = self._analyze_readability(
            structured_data,
            metrics
        )
        suggestions.extend(readability_suggestions)

        # 5. 生成分组报告
        report = self._create_report(suggestions)

        logger.info(f"Generated {len(suggestions)} optimization suggestions")

        return report

    def _analyze_headlines(
        self,
        data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """
        分析标题并生成优化建议

        检查维度：
        - 标题长度
        - 标题字号
        - 标题位置
        - 多级标题层次
        """
        suggestions = []
        articles = data.get('articles', [])

        for idx, article in enumerate(articles):
            article_id = article.get('id', f'article_{idx}')

            # 检查标题
            headline = self._get_article_headline(article, data)
            if not headline:
                continue

            # 1. 标题长度建议
            headline_text = self._extract_text(headline, data)
            if headline_text:
                length_suggestion = self._check_headline_length(
                    headline_text, article_id, headline
                )
                if length_suggestion:
                    suggestions.append(length_suggestion)

            # 2. 标题字号建议
            font_size = headline.get('font_size', 0)
            if font_size > 0:
                size_suggestion = self._check_headline_font_size(
                    font_size, article_id, headline
                )
                if size_suggestion:
                    suggestions.append(size_suggestion)

            # 3. 标题位置建议
            position_suggestion = self._check_headline_position(
                headline, article_id, data
            )
            if position_suggestion:
                suggestions.append(position_suggestion)

        return suggestions

    def _analyze_layout_balance(
        self,
        data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """
        分析版面平衡并生成优化建议

        检查维度：
        - 左右版面内容平衡
        - 上下版面平衡
        - 重心位置
        """
        suggestions = []

        # 1. 左右平衡
        left_right_balance = self._check_left_right_balance(data)
        if left_right_balance:
            suggestions.append(left_right_balance)

        # 2. 上下平衡
        top_bottom_balance = self._check_top_bottom_balance(data)
        if top_bottom_balance:
            suggestions.append(top_bottom_balance)

        # 3. 版面重心
        center_of_gravity = self._check_center_of_gravity(data)
        if center_of_gravity:
            suggestions.append(center_of_gravity)

        return suggestions

    def _analyze_visual_hierarchy(
        self,
        data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """
        分析视觉层次并生成优化建议

        检查维度：
        - 标题、副标题、正文的字号层次
        - 字体使用的一致性
        - 重点内容的突出程度
        """
        suggestions = []

        # 1. 字号层次检查
        hierarchy_suggestion = self._check_font_hierarchy(data)
        if hierarchy_suggestion:
            suggestions.append(hierarchy_suggestion)

        # 2. 字体一致性
        consistency_suggestion = self._check_font_consistency(data)
        if consistency_suggestion:
            suggestions.append(consistency_suggestion)

        return suggestions

    def _analyze_readability(
        self,
        data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """
        分析可读性并生成优化建议

        检查维度：
        - 分栏合理性
        - 正文长度
        - 段落划分
        """
        suggestions = []

        # 1. 分栏建议
        column_suggestion = self._check_column_structure(data, metrics)
        if column_suggestion:
            suggestions.append(column_suggestion)

        # 2. 正文长度建议
        body_length_suggestion = self._check_body_length(data)
        if body_length_suggestion:
            suggestions.append(body_length_suggestion)

        return suggestions

    # ───────────────────────────────────────────────────────────
    # 辅助方法
    # ───────────────────────────────────────────────────────────

    def _get_article_headline(self, article: Dict, data: Dict) -> Dict:
        """获取文章的标题block"""
        headline_id = article.get('headline_block_id')
        if headline_id:
            blocks = data.get('blocks', [])
            for block in blocks:
                if block.get('id') == headline_id:
                    return block
        return {}

    def _extract_text(self, block: Dict, data: Dict) -> str:
        """提取block的文本"""
        return block.get('text', '').strip()

    def _check_headline_length(
        self,
        text: str,
        article_id: str,
        headline: Dict
    ) -> OptimizationSuggestion:
        """检查标题长度"""
        length = len(text)

        # 获取配置的阈值
        max_length = self.headline_rules.get('max_length', 20)
        ideal_length = self.headline_rules.get('ideal_length', 12)

        if length > max_length:
            # 截断过长的标题用于显示（最多显示30字）
            display_text = text if len(text) <= 30 else text[:30] + "..."

            return OptimizationSuggestion(
                id=f"opt_headline_length_{article_id}",
                category=OptimizationCategory.HEADLINE,
                priority=OptimizationPriority.MEDIUM,
                title="标题长度偏长",
                description=f"标题《{display_text}》长度为{length}字，建议不超过{max_length}字",
                current_state=f"标题《{display_text}》：{length}字",
                suggested_state=f"建议精简到{ideal_length}-{max_length}字",
                benefit="简短的标题更有冲击力，易于读者快速抓住要点",
                affected_elements=[f"article_id:{article_id}"],
                confidence=0.8,
                metadata={
                    'headline_text': text,
                    'article_id': article_id
                }
            )

        return None

    def _check_headline_font_size(
        self,
        font_size: float,
        article_id: str,
        headline: Dict
    ) -> OptimizationSuggestion:
        """检查标题字号"""
        # 获取配置
        min_size = self.headline_rules.get('min_font_size', 14)
        max_size = self.headline_rules.get('max_font_size', 24)

        # 提取标题文本
        text = self._extract_text(headline, {})
        display_text = text if len(text) <= 30 else text[:30] + "..."

        if font_size < min_size:
            return OptimizationSuggestion(
                id=f"opt_headline_size_{article_id}",
                category=OptimizationCategory.HEADLINE,
                priority=OptimizationPriority.MEDIUM,
                title="标题字号偏小",
                description=f"标题《{display_text}》字号为{font_size:.1f}pt，建议增大到{min_size}pt以上",
                current_state=f"标题《{display_text}》：{font_size:.1f}pt",
                suggested_state=f"建议字号：{min_size}-{max_size}pt",
                benefit="较大的字号能增强标题的视觉冲击力",
                affected_elements=[f"article_id:{article_id}"],
                confidence=0.9,
                metadata={
                    'headline_text': text,
                    'article_id': article_id,
                    'font_size': font_size
                }
            )

        return None

    def _check_headline_position(
        self,
        headline: Dict,
        article_id: str,
        data: Dict
    ) -> OptimizationSuggestion:
        """检查标题位置"""
        # 这里可以添加更复杂的位置检查逻辑
        # 例如：标题是否在文章顶部、是否居中等
        return None

    def _check_left_right_balance(
        self,
        data: Dict
    ) -> OptimizationSuggestion:
        """检查左右平衡"""
        # 计算左右版面的内容密度
        blocks = data.get('blocks', [])
        page_width = data.get('width', 965)

        left_blocks = [b for b in blocks if b.get('x0', 0) < page_width / 2]
        right_blocks = [b for b in blocks if b.get('x0', 0) >= page_width / 2]

        left_area = sum(
            (b.get('x1', 0) - b.get('x0', 0)) * (b.get('y1', 0) - b.get('y0', 0))
            for b in left_blocks
        )
        right_area = sum(
            (b.get('x1', 0) - b.get('x0', 0)) * (b.get('y1', 0) - b.get('y0', 0))
            for b in right_blocks
        )

        if left_area > 0 and right_area > 0:
            ratio = left_area / right_area
            # 如果左右差异超过20%
            if ratio > 1.2 or ratio < 0.83:
                heavier = "左侧" if ratio > 1 else "右侧"
                return OptimizationSuggestion(
                    id="opt_layout_balance",
                    category=OptimizationCategory.LAYOUT_BALANCE,
                    priority=OptimizationPriority.LOW,
                    title=f"{heavier}版面内容偏多",
                    description=f"左右版面内容比例为{ratio:.2f}:1，建议调整到更平衡的状态",
                    current_state=f"当前比例：{ratio:.2f}:1",
                    suggested_state="建议比例：0.9:1 到 1.1:1之间",
                    benefit="平衡的版面更美观，阅读体验更好",
                    confidence=0.7
                )

        return None

    def _check_top_bottom_balance(self, data: Dict) -> OptimizationSuggestion:
        """检查上下平衡"""
        # TODO: 实现上下平衡检查
        return None

    def _check_center_of_gravity(self, data: Dict) -> OptimizationSuggestion:
        """检查版面重心"""
        # TODO: 实现重心检查
        return None

    def _check_font_hierarchy(self, data: Dict) -> OptimizationSuggestion:
        """检查字号层次"""
        font_profile = data.get('font_profile', {})

        # font_profile结构：{'headline': [min, max, avg], 'body': [min, max, avg]}
        headline_stats = font_profile.get('headline', [])
        body_stats = font_profile.get('body', [])

        if len(headline_stats) >= 3 and len(body_stats) >= 3:
            headline_avg = headline_stats[2]  # [min, max, avg]
            body_avg = body_stats[2]

            if headline_avg > 0 and body_avg > 0:
                ratio = headline_avg / body_avg

                # 标题与正文的字号比例建议在1.5-2.0之间
                if ratio < 1.5:
                    return OptimizationSuggestion(
                        id="opt_font_hierarchy",
                        category=OptimizationCategory.VISUAL_HIERARCHY,
                        priority=OptimizationPriority.MEDIUM,
                        title="标题与正文字号差异偏小",
                        description=f"标题字号({headline_avg:.1f}pt)是正文({body_avg:.1f}pt)的{ratio:.2f}倍，建议增大差异",
                        current_state=f"当前比例：{ratio:.2f}:1",
                        suggested_state="建议比例：1.5:1 到 2.0:1",
                        benefit="清晰的字号层次能增强版面的视觉引导",
                        confidence=0.8
                    )

        return None

    def _check_font_consistency(self, data: Dict) -> OptimizationSuggestion:
        """检查字体一致性"""
        # TODO: 实现字体一致性检查
        return None

    def _check_column_structure(
        self,
        data: Dict,
        metrics: Dict
    ) -> OptimizationSuggestion:
        """检查分栏结构"""
        # 获取分栏信息
        articles = data.get('articles', [])

        # 统计文章的分栏数
        column_counts = []
        for article in articles:
            # 这里可以添加更复杂的分栏分析
            pass

        # TODO: 实现分栏建议
        return None

    def _check_body_length(self, data: Dict) -> OptimizationSuggestion:
        """检查正文长度"""
        # TODO: 实现正文长度检查
        return None

    def _create_report(
        self,
        suggestions: List[OptimizationSuggestion]
    ) -> OptimizationReport:
        """
        创建优化建议报告

        Args:
            suggestions: 所有建议列表

        Returns:
            OptimizationReport对象
        """
        # 统计各级优先级的数量
        high_count = sum(1 for s in suggestions if s.priority == OptimizationPriority.HIGH)
        medium_count = sum(1 for s in suggestions if s.priority == OptimizationPriority.MEDIUM)
        low_count = sum(1 for s in suggestions if s.priority == OptimizationPriority.LOW)

        # 按类别分组
        headline_suggestions = [
            s for s in suggestions
            if s.category == OptimizationCategory.HEADLINE
        ]
        layout_suggestions = [
            s for s in suggestions
            if s.category == OptimizationCategory.LAYOUT_BALANCE
        ]
        visual_suggestions = [
            s for s in suggestions
            if s.category == OptimizationCategory.VISUAL_HIERARCHY
        ]
        readability_suggestions = [
            s for s in suggestions
            if s.category == OptimizationCategory.READABILITY
        ]

        # 计算优化评分
        # 基础分100，每个HIGH建议扣5分，MEDIUM扣2分，LOW扣1分
        optimization_score = max(0, 100 - high_count * 5 - medium_count * 2 - low_count * 1)

        # 确定优化潜力
        if high_count >= 3 or medium_count >= 5:
            potential = "高"
        elif high_count >= 1 or medium_count >= 2:
            potential = "中"
        else:
            potential = "低"

        return OptimizationReport(
            suggestions=suggestions,
            total_count=len(suggestions),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            headline_suggestions=headline_suggestions,
            layout_suggestions=layout_suggestions,
            visual_suggestions=visual_suggestions,
            readability_suggestions=readability_suggestions,
            optimization_score=optimization_score,
            optimization_potential=potential
        )
