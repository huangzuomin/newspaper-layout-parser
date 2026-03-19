"""
标题重写策略引擎
Headline Rewrite Strategy Engine

基于规则和模板生成标题重写候选
"""

import re
import logging
from typing import List, Dict, Any

from ..models.headline_rewrite import (
    RewriteStyle,
    RewriteCandidate,
    HeadlineContext,
    RiskLevel,
    PolicyConstraints
)
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger("intelligent_editor")


class RewriteStrategyEngine:
    """标题重写策略引擎"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化策略引擎

        Args:
            config: 配置字典
        """
        if config is None:
            config = ConfigLoader.load_config('rewrite_templates.yaml')

        self.config = config

        # 加载重写规则
        self.meeting_style_rewrites = config.get('meeting_style_rewrites', [])
        self.generic_word_removal = config.get('generic_word_removal', [])
        self.conservative_templates = config.get('conservative_templates', [])
        self.focused_templates = config.get('focused_templates', [])
        self.people_oriented_templates = config.get('people_oriented_templates', [])

        # 加载风险控制规则
        self.forbidden_expressions = config.get('risk_control', {}).get('forbidden_expressions', [])

        logger.info("RewriteStrategyEngine initialized")

    def generate_rewrites(
        self,
        context: HeadlineContext
    ) -> List[RewriteCandidate]:
        """
        生成标题重写候选

        Args:
            context: 标题上下文

        Returns:
            候选标题列表
        """
        candidates = []

        # 为每种风格生成候选
        conservative_candidate = self._generate_conservative(context)
        if conservative_candidate:
            candidates.append(conservative_candidate)

        focused_candidate = self._generate_focused(context)
        if focused_candidate:
            candidates.append(focused_candidate)

        # 仅在合适的情况下生成民生导向型
        if self._should_generate_people_oriented(context):
            people_candidate = self._generate_people_oriented(context)
            if people_candidate:
                candidates.append(people_candidate)

        return candidates

    def _generate_conservative(
        self,
        context: HeadlineContext
    ) -> RewriteCandidate:
        """
        生成稳健型标题

        特点：
        - 最接近原稿气质
        - 政治安全边界最稳
        - 适合主稿、政务稿
        """
        headline = context.headline_text

        # 1. 应用会议体重写规则
        for rule in self.meeting_style_rewrites:
            pattern = rule.get('pattern')
            replacement = rule.get('replacement', '')
            if pattern in headline:
                headline = headline.replace(pattern, replacement)
                break  # 只应用第一个匹配的规则

        # 2. 删除虚词（优先级1）
        for word_rule in self.generic_word_removal:
            if word_rule.get('priority') == 1:
                word = word_rule.get('word')
                if word in headline:
                    headline = headline.replace(word, '')

        # 3. 清理多余空格
        headline = headline.strip()

        # 4. 验证长度
        if len(headline) > 20:
            # 进一步删除优先级2的虚词
            for word_rule in self.generic_word_removal:
                if word_rule.get('priority') == 2:
                    word = word_rule.get('word')
                    if word in headline:
                        headline = headline.replace(word, '')
                        if len(headline) <= 20:
                            break

        # 5. 生成候选
        changes = self._describe_changes(context.headline_text, headline)
        is_safe, risk_reasons = self._check_risk(headline)

        candidate = RewriteCandidate(
            version=1,
            headline=headline,
            style=RewriteStyle.CONSERVATIVE,
            changes=changes,
            risk_note="稳妥" if is_safe else "需审看：" + "、".join(risk_reasons),
            risk_level=RiskLevel.SAFE if is_safe else RiskLevel.USABLE_WITH_REVIEW,
            confidence=0.85,
            source="rule"
        )

        return candidate

    def _generate_focused(
        self,
        context: HeadlineContext
    ) -> RewriteCandidate:
        """
        生成聚焦型标题

        特点：
        - 突出核心动作、结果、对象
        - 适合把抽象标题收紧
        - 信息密度更高
        """
        headline = context.headline_text

        # 1. 删除会议体表述
        for rule in self.meeting_style_rewrites:
            pattern = rule.get('pattern')
            replacement = rule.get('replacement', '')
            headline = headline.replace(pattern, replacement)

        # 2. 删除所有虚词
        for word_rule in self.generic_word_removal:
            word = word_rule.get('word')
            headline = headline.replace(word, '')

        # 3. 提取核心动作和对象
        # 查找关键动词
        action_patterns = [
            r'(部署|推进|落实|加强|深化|提升|改善|优化|研究|学习贯彻)',
            r'(召开|举办|举行)',  # 这些通常要删除
        ]

        action_match = None
        for pattern in action_patterns:
            match = re.search(pattern, headline)
            if match:
                action_match = match.group(1)
                break

        # 4. 构建聚焦型标题
        if action_match and action_match not in ['召开', '举办', '举行']:
            # 保留动作+对象
            focused_headline = headline

            # 删除冗余词
            redundant_patterns = ['等相关工作', '等有关工作', '等工作', '相关工作']
            for pattern in redundant_patterns:
                focused_headline = focused_headline.replace(pattern, '工作')

            focused_headline = focused_headline.strip()
        else:
            # 回退到简单删除
            focused_headline = headline

        # 5. 验证
        if len(focused_headline) < 6 or len(focused_headline) > 20:
            # 如果不满足长度要求，返回None
            return None

        changes = self._describe_changes(context.headline_text, focused_headline)
        is_safe, risk_reasons = self._check_risk(focused_headline)

        candidate = RewriteCandidate(
            version=2,
            headline=focused_headline,
            style=RewriteStyle.FOCUSED,
            changes=changes,
            risk_note="可用但需审看" if is_safe else "需审看：" + "、".join(risk_reasons),
            risk_level=RiskLevel.USABLE_WITH_REVIEW,
            confidence=0.75,
            source="rule"
        )

        return candidate

    def _generate_people_oriented(
        self,
        context: HeadlineContext
    ) -> RewriteCandidate:
        """
        生成民生导向型标题

        特点：
        - 强调群众感受、现实落点
        - 只适用于合适的民生稿
        - 不得过度口语化
        """
        headline = context.headline_text

        # 从模板中生成
        if not self.people_oriented_templates:
            return None

        # 尝试匹配模板
        for template_rule in self.people_oriented_templates:
            template = template_rule.get('template', '')

            # 简单的模板匹配
            if '{achievement}' in template:
                # 尝试从导语提取成就
                if context.lead_text:
                    achievement = self._extract_achievement_from_lead(context.lead_text)
                    if achievement:
                        new_headline = template.format(achievement=achievement)
                    else:
                        continue
                else:
                    continue
            elif '{focus}' in template:
                # 提取焦点
                focus = self._extract_focus(headline)
                if focus:
                    new_headline = template.format(focus=focus)
                else:
                    continue
            elif '{action}' in template:
                # 提取动作
                action = self._extract_action(headline)
                if action:
                    new_headline = template.format(action=action)
                else:
                    continue
            elif '{quality}' in template:
                # 质量提升类
                quality = "群众生活质量"
                new_headline = template.format(quality=quality)
            else:
                continue

            # 验证长度
            if len(new_headline) < 6 or len(new_headline) > 20:
                continue

            changes = self._describe_changes(context.headline_text, new_headline)
            is_safe, risk_reasons = self._check_risk(new_headline)

            candidate = RewriteCandidate(
                version=3,
                headline=new_headline,
                style=RewriteStyle.PEOPLE_ORIENTED,
                changes=changes,
                risk_note="需审看：确认是否适合民生导向" if is_safe else "需审看：" + "、".join(risk_reasons),
                risk_level=RiskLevel.USABLE_WITH_REVIEW,
                confidence=0.70,
                source="rule"
            )

            return candidate

        return None

    def _should_generate_people_oriented(self, context: HeadlineContext) -> bool:
        """判断是否应该生成民生导向型标题"""
        # 如果导语包含民生关键词，可以生成
        people_keywords = [
            '民生', '群众', '居民', '市民',
            '福祉', '获得感', '幸福感',
            '就业', '医疗', '教育', '住房'
        ]

        if context.lead_text:
            for keyword in people_keywords:
                if keyword in context.lead_text:
                    return True

        return False

    def _extract_achievement_from_lead(self, lead_text: str) -> str:
        """从导语提取成就"""
        # 简单提取：查找关键词后的内容
        patterns = [
            r'成果(.*?)，',
            r'成效(.*?)，',
            r'进展(.*?)，',
        ]

        for pattern in patterns:
            match = re.search(pattern, lead_text)
            if match:
                achievement = match.group(1).strip()
                if len(achievement) > 2 and len(achievement) < 10:
                    return achievement

        return ""

    def _extract_focus(self, headline: str) -> str:
        """提取焦点"""
        # 删除虚词后的剩余部分
        focus = headline
        for word_rule in self.generic_word_removal:
            word = word_rule.get('word')
            focus = focus.replace(word, '')

        # 删除会议体
        for rule in self.meeting_style_rewrites:
            pattern = rule.get('pattern')
            focus = focus.replace(pattern, '')

        focus = focus.strip()

        if len(focus) > 2 and len(focus) < 10:
            return focus

        return ""

    def _extract_action(self, headline: str) -> str:
        """提取动作"""
        actions = ['推进', '加强', '提升', '改善', '办好', '落实']
        for action in actions:
            if action in headline:
                return action

        return ""

    def _describe_changes(self, original: str, new: str) -> str:
        """描述改动"""
        changes = []

        # 检查删除的内容
        if '会议召开' in original and '会议召开' not in new:
            changes.append('删除"会议召开"')

        if '会议强调' in original and '会议强调' not in new:
            changes.append('删除"会议强调"')

        # 检查虚词删除
        generic_words = ['进一步', '切实', '扎实', '全面']
        for word in generic_words:
            if word in original and word not in new:
                changes.append(f'删除"{word}"')
                break  # 只记录一个

        if not changes:
            if len(new) < len(original):
                changes.append('精简表述')
            else:
                changes.append('调整表述')

        return '；'.join(changes)

    def _check_risk(self, headline: str) -> tuple:
        """检查标题风险"""
        risk_reasons = []
        is_safe = True

        # 检查禁用表达
        for expr in self.forbidden_expressions:
            if expr in headline:
                risk_reasons.append(f'包含禁用词：{expr}')
                is_safe = False

        # 检查长度
        if len(headline) > 20:
            risk_reasons.append(f'标题过长（{len(headline)}字）')
            is_safe = False

        if len(headline) < 6:
            risk_reasons.append(f'标题过短（{len(headline)}字）')
            is_safe = False

        return is_safe, risk_reasons
