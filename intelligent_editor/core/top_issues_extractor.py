"""
Top问题提取器
Top Issues Extractor - 信息压缩优先
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

from ..models.risk import Risk, Severity
from ..models.decision import Decision, DecisionType

logger = logging.getLogger("intelligent_editor")


@dataclass
class TopIssue:
    """Top问题对象"""
    rank: int  # 排名 1/2/3
    risk: Risk  # 关联的风险对象

    # 信息压缩
    summary: str  # 一句话总结（≤20字）
    action_needed: str  # 需要采取的行动（≤15字）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'rank': self.rank,
            'severity': self.risk.severity.name,
            'summary': self.summary,
            'action_needed': self.action_needed,
            'affected_elements': self.risk.affected_elements,
        }


class TopIssuesExtractor:
    """
    Top问题提取器

    从risks中筛选Top 3最重要的问题，
    实现信息压缩优先原则。
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Top问题提取器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.max_issues = self.config.get('max_issues', 3)

        logger.info(f"TopIssuesExtractor initialized with max_issues={self.max_issues}")

    def extract_top_issues(
        self,
        risks: List[Risk],
        decision: Decision
    ) -> List[TopIssue]:
        """
        提取Top N问题

        Args:
            risks: 所有风险
            decision: 决策对象

        Returns:
            TopIssue列表（最多3个）
        """
        if not risks:
            logger.info("No risks to extract")
            return []

        # 1. 过滤：根据决策类型过滤风险
        filtered_risks = self._filter_risks(risks, decision)

        logger.info(f"Filtered {len(filtered_risks)} risks from {len(risks)} total")

        # 2. 排序：按severity和影响范围排序
        sorted_risks = self._sort_risks(filtered_risks)

        # 3. 选择Top N
        top_risks = sorted_risks[:self.max_issues]

        # 4. 转换为TopIssue对象
        top_issues = [
            TopIssue(
                rank=i + 1,
                risk=risk,
                summary=self._generate_summary(risk),
                action_needed=self._suggest_action(risk)
            )
            for i, risk in enumerate(top_risks)
        ]

        logger.info(f"Extracted {len(top_issues)} top issues")

        return top_issues

    def _filter_risks(
        self,
        risks: List[Risk],
        decision: Decision
    ) -> List[Risk]:
        """
        根据决策类型过滤风险

        - REJECT: 只显示CRITICAL
        - REVIEW: 显示CRITICAL + HIGH
        - APPROVE: 显示HIGH + MEDIUM

        Args:
            risks: 所有风险
            decision: 决策对象

        Returns:
            过滤后的风险列表
        """
        if decision.type == DecisionType.REJECT:
            # 只显示CRITICAL
            return [r for r in risks if r.severity == Severity.CRITICAL]

        elif decision.type == DecisionType.REVIEW:
            # 显示CRITICAL + HIGH
            return [r for r in risks if r.severity in [Severity.CRITICAL, Severity.HIGH]]

        else:  # APPROVE
            # 显示HIGH + MEDIUM
            return [r for r in risks if r.severity in [Severity.HIGH, Severity.MEDIUM]]

    def _sort_risks(self, risks: List[Risk]) -> List[Risk]:
        """
        按severity和影响范围排序

        Args:
            risks: 风险列表

        Returns:
            排序后的风险列表
        """
        # 排序规则：
        # 1. 先按severity排序（从高到低）
        # 2. 同级按受影响元素数量排序（从多到少）
        # 3. 再按confidence排序（从高到低）

        def sort_key(risk: Risk):
            return (
                -risk.severity_score,  # 负号表示降序
                -len(risk.affected_elements),
                -risk.confidence
            )

        return sorted(risks, key=sort_key)

    def _generate_summary(self, risk: Risk) -> str:
        """
        生成一句话总结（≤20字）

        Args:
            risk: 风险对象

        Returns:
            总结文本
        """
        # 提取关键信息
        risk_type = risk.type.replace('_', ' ')

        # 如果有affected_elements，添加到summary中
        if risk.affected_elements:
            element = risk.affected_elements[0]
            # 提取ID部分（如"article:a_left_zone_2" → "a_left_zone_2"）
            if ':' in element:
                element = element.split(':')[1]
            return f"{element} {risk_type}"

        # 否则只返回风险类型
        return risk_type

    def _suggest_action(self, risk: Risk) -> str:
        """
        生成行动建议（≤15字）

        Args:
            risk: 风险对象

        Returns:
            行动建议文本
        """
        # 如果风险对象有fix_suggestion，从中提取关键信息
        if risk.fix_suggestion:
            # 截取前15个字符
            suggestion = risk.fix_suggestion[:15]
            # 确保不在汉字中间截断
            if len(suggestion) == 15 and len(risk.fix_suggestion) > 15:
                suggestion = suggestion.rsplit(' ', 1)[0]
            return suggestion

        # 否则根据风险类型生成建议
        risk_type = risk.type

        action_map = {
            'missing_headline': '检查article聚类',
            'too_few_body_blocks': '检查block分类',
            'narrow_column': '调整分栏参数',
            'too_many_columns': '调整分栏策略',
            'zone_without_headline': '检查zone分类',
            'empty_block': '检查文本提取',
        }

        return action_map.get(risk_type, '请人工检查')
