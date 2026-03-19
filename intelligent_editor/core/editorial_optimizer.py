"""
Turn quality findings into executive-facing editorial tasks.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .candidate_guardrail import CandidateGuardrail
from .optimization_llm_generator import OptimizationLLMGenerator
from ..models.editorial_quality import (
    HeadlineSuggestion,
    LeadSuggestion,
    PackagingSuggestion,
    QualityImprovementReport,
)
from ..models.executive_report import OptimizationOption, OptimizationReport, OptimizationTask


class EditorialOptimizer:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        generator: Optional[Any] = None,
    ):
        self.raw_config = config or {}
        self.generator = generator or OptimizationLLMGenerator(self.raw_config)
        self.guardrail = CandidateGuardrail()

    def build_report(self, quality_report: QualityImprovementReport) -> OptimizationReport:
        tasks: List[OptimizationTask] = []
        tasks.extend(self._build_headline_tasks(quality_report.headline_suggestions))
        tasks.extend(self._build_lead_tasks(quality_report.lead_suggestions))
        tasks.extend(self._build_packaging_tasks(quality_report.packaging_suggestions))

        tasks = tasks[:3]
        summary = "聚焦最值得总编辑处理的编辑任务，并尽量提供可直接讨论的方案选项。"
        note = (
            "Phase 3 已接入可选的大模型候选生成；模型不可用或候选未通过约束时，将回退到规则方案。"
        )
        return OptimizationReport(summary=summary, tasks=tasks, note=note)

    def _build_headline_tasks(
        self, suggestions: List[HeadlineSuggestion]
    ) -> List[OptimizationTask]:
        if not suggestions:
            return []

        article_ids = [item.article_id for item in suggestions]
        primary = suggestions[0]
        options = self._build_headline_options(primary, suggestions)

        return [
            OptimizationTask(
                id="headline_rewrite_task",
                priority="high",
                title=f"重点标题建议重写（涉及{len(article_ids)}篇稿件）",
                why_it_matters="当前重点稿标题存在长度或表达问题，会直接影响总编辑对版面主次和传播力的判断。",
                task_type="headline",
                article_ids=article_ids,
                options=options[:3],
                source="phase3_hybrid" if any(item.source == "llm" for item in options) else "phase1_rule",
            )
        ]

    def _build_headline_options(
        self,
        primary: HeadlineSuggestion,
        suggestions: List[HeadlineSuggestion],
    ) -> List[OptimizationOption]:
        llm_options = self._generate_llm_options(
            task_type="headline",
            article_id=primary.article_id,
            original_text=primary.headline_text,
            issue=primary.issue_description,
            reason=primary.reason,
            suggestion=primary.lightweight_suggestion,
            extra={
                "alternative_headlines": primary.alternative_headlines,
                "issue_tags": [item.issue_type.value for item in suggestions[:3]],
            },
        )
        if llm_options:
            return llm_options

        options: List[OptimizationOption] = []
        for suggestion in suggestions:
            headline_options = self._extract_headline_options(
                suggestion.alternative_headlines
            )
            for index, option in enumerate(headline_options[:2], start=1):
                options.append(
                    OptimizationOption(
                        label=f"标题方案 {index}",
                        content=option,
                        rationale="基于现有标题问题生成的替代表达。",
                        fit_for="适合讨论头条或重点稿标题重写方向",
                        source="rule_rewrite",
                    )
                )

        if not options:
            options.append(
                OptimizationOption(
                    label="标题方向",
                    content=primary.lightweight_suggestion,
                    rationale="当前还没有足够可用的重写候选，先给出改稿方向。",
                    fit_for="适合编辑部内部快速定方向",
                    source="rule_direction",
                )
            )
        return options

    def _extract_headline_options(self, raw_options: Iterable[str]) -> List[str]:
        normalized = []
        for item in raw_options:
            line = item.splitlines()[0].strip()
            if "] " in line:
                line = line.split("] ", 1)[1]
            normalized.append(line)
        return self.guardrail.filter(normalized)

    def _build_lead_tasks(self, suggestions: List[LeadSuggestion]) -> List[OptimizationTask]:
        if not suggestions:
            return []

        article_ids: List[str] = []
        for item in suggestions:
            if item.article_id not in article_ids:
                article_ids.append(item.article_id)

        primary = suggestions[0]
        options = self._build_lead_options(primary, article_ids)

        return [
            OptimizationTask(
                id="lead_rewrite_task",
                priority="high",
                title=f"重点稿导语建议重写（涉及{len(article_ids)}篇稿件）",
                why_it_matters="导语没有尽早交代核心事实，会削弱总编辑最关心的新闻力度和阅读抓手。",
                task_type="lead",
                article_ids=article_ids,
                options=options[:3],
                source="phase3_hybrid" if any(item.source == "llm" for item in options) else "phase1_rule",
            )
        ]

    def _build_lead_options(
        self, primary: LeadSuggestion, article_ids: List[str]
    ) -> List[OptimizationOption]:
        llm_options = self._generate_llm_options(
            task_type="lead",
            article_id=primary.article_id,
            original_text=primary.lead_text,
            issue=primary.issue_description,
            reason=primary.reason,
            suggestion=primary.lightweight_suggestion,
            extra={"revised_lead_example": primary.revised_lead_example},
        )
        if llm_options:
            return llm_options

        options = [
            OptimizationOption(
                label="导语改写方向",
                content=primary.lightweight_suggestion,
                rationale="优先把最关键的结果、变化或影响提前。",
                fit_for="适合头条、二条和重点稿导语优化",
                source="rule_direction",
            )
        ]
        if primary.revised_lead_example:
            options.append(
                OptimizationOption(
                    label="导语示例",
                    content=primary.revised_lead_example,
                    rationale="提供一个最低可用的导语改写起点。",
                    fit_for="适合编辑快速起稿再人工润色",
                    source="rule_template",
                )
            )
        if len(article_ids) > 1:
            options.append(
                OptimizationOption(
                    label="共性处理",
                    content="优先统一把结果、变化、影响前置，再逐篇做语气细化。",
                    rationale="当前是页面级共性问题，适合先统一改法再细调。",
                    fit_for="适合多篇重点稿一起快速提升导语抓手",
                    source="rule_direction",
                )
            )
        return options

    def _build_packaging_tasks(
        self, suggestions: List[PackagingSuggestion]
    ) -> List[OptimizationTask]:
        if not suggestions:
            return []

        primary = suggestions[0]
        return [
            OptimizationTask(
                id="packaging_task",
                priority="medium",
                title="版面包装建议补强",
                why_it_matters="即使稿件成立，版面包装不足也会削弱重点稿的呈现力度。",
                task_type="packaging",
                article_ids=[],
                options=[
                    OptimizationOption(
                        label="包装方向",
                        content=primary.lightweight_suggestion,
                        rationale=primary.reason,
                        fit_for="适合版式编辑与总编辑协同判断是否需要调整视觉支撑",
                        source="rule_direction",
                    )
                ],
                source="phase1_rule",
            )
        ]

    def _generate_llm_options(
        self,
        task_type: str,
        article_id: str,
        original_text: str,
        issue: str,
        reason: str,
        suggestion: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> List[OptimizationOption]:
        if not self.generator.is_available():
            return []

        payload = {
            "task_type": task_type,
            "article_id": article_id,
            "original_text": original_text,
            "issue": issue,
            "reason": reason,
            "rule_suggestion": suggestion,
            "constraints": {
                "max_length": self.guardrail.max_length,
                "forbidden_terms": list(self.guardrail.forbidden_terms),
            },
        }
        if extra:
            payload["extra"] = extra

        try:
            response = self.generator.generate(payload)
        except Exception:
            return []

        options: List[OptimizationOption] = []
        for item in response.get("options", []):
            content = str(item.get("content", "")).strip()
            if task_type == "headline" and not self.guardrail.allow(content):
                continue
            if task_type == "lead" and not content:
                continue
            options.append(
                OptimizationOption(
                    label=str(item.get("label", "方案")),
                    content=content,
                    rationale=str(item.get("rationale", "基于问题生成的优化方案。")),
                    fit_for=str(item.get("fit_for", "适合总编辑审看后交编辑落稿。")),
                    source="llm",
                )
            )
        return options
