"""
Executive-facing safety evaluator with rule baseline plus semantic LLM review.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .semantic_safety_reviewer import SemanticSafetyReviewer
from ..models.executive_report import SafetyFinding, SafetyReport


class SafetyEvaluator:
    """
    Phase 2 safety evaluator.

    Rule findings remain the engineering baseline. When enabled, a semantic
    reviewer adds executive-facing findings about orientation, political wording,
    and statement safety. If the semantic chain is unavailable, the report falls
    back to mandatory manual review.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        reviewer: Optional[Any] = None,
    ):
        self.raw_config = config or {}
        self.config = self.raw_config.get("safety_evaluation", self.raw_config)
        self.reviewer = reviewer or SemanticSafetyReviewer(self.config)
        self.max_articles = int(self.config.get("max_articles", 5))
        self.max_body_chars = int(self.config.get("max_body_chars", 220))

    def evaluate(
        self,
        decision: Any,
        top_issues: List[Any],
        risks: List[Any],
        structured_data: Optional[Dict[str, Any]] = None,
    ) -> SafetyReport:
        baseline_findings = self._build_rule_findings(top_issues)
        semantic_result = None
        semantic_enabled = False
        semantic_failure: Optional[str] = None

        if structured_data is not None and self.reviewer.is_available():
            try:
                semantic_result = self.reviewer.review(
                    self._build_review_payload(
                        decision,
                        top_issues,
                        risks,
                        structured_data,
                    )
                )
                semantic_enabled = True
            except Exception as exc:
                semantic_failure = str(exc)

        if semantic_result:
            findings = baseline_findings + self._build_semantic_findings(semantic_result)
            requires_manual_review = bool(
                semantic_result.get("requires_manual_review", True)
            )
            summary = semantic_result.get(
                "summary",
                "已结合规则底线与语义安全评估生成总编辑安全意见。",
            )
            recommendation = semantic_result.get(
                "recommendation", decision.type.value
            ).lower()
            risk_level = semantic_result.get("risk_level", decision.risk_level.name)
            note = semantic_result.get(
                "note",
                "语义安全链已启用，建议结合人工终审理解模型结论。",
            )
        else:
            findings = baseline_findings + [self._build_manual_review_placeholder()]
            requires_manual_review = True
            summary = (
                "当前安全意见仍以规则底线和工程风险为主，不能替代导向与政治表达终审。"
            )
            recommendation = decision.type.value
            risk_level = decision.risk_level.name
            note = (
                f"规则层识别到 {len(risks)} 条底线风险；"
                + (
                    f"语义安全评估调用失败：{semantic_failure}"
                    if semantic_failure
                    else "语义安全评估尚未启用。"
                )
            )

        return SafetyReport(
            recommendation=recommendation,
            risk_level=risk_level,
            summary=summary,
            findings=findings,
            semantic_review_enabled=semantic_enabled,
            requires_manual_review=requires_manual_review,
            note=note,
        )

    def _build_rule_findings(self, top_issues: Iterable[Any]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        for issue in list(top_issues)[:3]:
            findings.append(
                SafetyFinding(
                    level=issue.risk.severity.name,
                    title=issue.summary,
                    detail=issue.risk.description,
                    action=issue.action_needed,
                    source="rule_baseline",
                    requires_manual_review=False,
                )
            )
        return findings

    def _build_semantic_findings(
        self, semantic_result: Dict[str, Any]
    ) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        for item in semantic_result.get("findings", []):
            findings.append(
                SafetyFinding(
                    level=str(item.get("level", "MANUAL_REVIEW")).upper(),
                    title=item.get("title", "语义安全需复核"),
                    detail=item.get("detail", ""),
                    action=item.get("action", "请人工复核该项表达风险。"),
                    source=item.get("source", "semantic_review"),
                    requires_manual_review=bool(
                        item.get("requires_manual_review", True)
                    ),
                )
            )
        return findings

    @staticmethod
    def _build_manual_review_placeholder() -> SafetyFinding:
        return SafetyFinding(
            level="MANUAL_REVIEW",
            title="导向与政治表达需人工/模型复核",
            detail="当前阶段仅完成规则底线，尚未形成稳定的语义安全放行能力。",
            action="上线前请对导向、政治表达、口径一致性进行专项复核。",
            source="semantic_fallback",
            requires_manual_review=True,
        )

    def _build_review_payload(
        self,
        decision: Any,
        top_issues: List[Any],
        risks: List[Any],
        structured_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        blocks = {
            block.get("id"): block for block in structured_data.get("blocks", []) if block.get("id")
        }
        articles = []
        for article in structured_data.get("articles", [])[: self.max_articles]:
            headline_text = self._get_block_text(blocks, article.get("headline_block_id"))
            subheadline_text = self._get_block_text(
                blocks, article.get("subheadline_block_id")
            )
            body_text = self._collect_body_text(blocks, article.get("body_block_ids", []))
            articles.append(
                {
                    "article_id": article.get("id"),
                    "headline": headline_text,
                    "subheadline": subheadline_text,
                    "body_summary": body_text[: self.max_body_chars],
                }
            )

        return {
            "decision": decision.type.value,
            "risk_level": decision.risk_level.name,
            "top_rule_findings": [
                {
                    "summary": issue.summary,
                    "detail": issue.risk.description,
                    "action": issue.action_needed,
                }
                for issue in list(top_issues)[:3]
            ],
            "rule_risk_count": len(risks),
            "articles": articles,
        }

    @staticmethod
    def _get_block_text(blocks: Dict[str, Dict[str, Any]], block_id: Optional[str]) -> str:
        if not block_id:
            return ""
        return str(blocks.get(block_id, {}).get("text", "")).strip()

    def _collect_body_text(
        self, blocks: Dict[str, Dict[str, Any]], body_block_ids: Iterable[str]
    ) -> str:
        parts: List[str] = []
        for block_id in body_block_ids:
            text = self._get_block_text(blocks, block_id)
            if text:
                parts.append(text)
        return " ".join(parts)
