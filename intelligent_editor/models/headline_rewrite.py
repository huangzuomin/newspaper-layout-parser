"""
Headline rewrite data models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RewriteStyle(Enum):
    CONSERVATIVE = "conservative"
    FOCUSED = "focused"
    PEOPLE_ORIENTED = "people_oriented"


class SuggestionType(Enum):
    DIRECTIONAL = "directional"
    MICRO_EDIT = "micro_edit"
    STRUCTURAL = "structural"


class RiskLevel(Enum):
    SAFE = "safe"
    USABLE_WITH_REVIEW = "usable_with_review"
    NOT_RECOMMENDED = "not_recommended"


@dataclass
class HeadlineDiagnosis:
    core_problem: str
    confidence: float
    issue_tags: List[str] = field(default_factory=list)
    analysis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_problem": self.core_problem,
            "confidence": self.confidence,
            "issue_tags": self.issue_tags,
            "analysis": self.analysis,
        }


@dataclass
class OptimizationSuggestion:
    type: SuggestionType
    message: str
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "message": self.message,
            "reasoning": self.reasoning,
        }


@dataclass
class RewriteCandidate:
    version: int
    headline: str
    style: RewriteStyle
    changes: str
    risk_note: str
    risk_level: RiskLevel
    confidence: float
    source: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "headline": self.headline,
            "style": self.style.value,
            "changes": self.changes,
            "risk_note": self.risk_note,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class HeadlineRewriteResult:
    article_id: str
    headline_block_id: str
    original_headline: str
    original_length: int
    need_optimization: bool
    diagnosis: Optional[HeadlineDiagnosis] = None
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    rewrite_candidates: List[RewriteCandidate] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "article_id": self.article_id,
            "headline_block_id": self.headline_block_id,
            "original_headline": self.original_headline,
            "original_length": self.original_length,
            "need_optimization": self.need_optimization,
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "rewrite_candidates": [candidate.to_dict() for candidate in self.rewrite_candidates],
            "metadata": self.metadata,
        }


@dataclass
class PolicyConstraints:
    tone: str = "serious_editorial"
    allow_aggressive_language: bool = False
    forbidden_words: List[str] = field(
        default_factory=lambda: ["sensational", "explosive", "must_read", "exposed"]
    )
    max_length: int = 20
    min_length: int = 6
    allow_hype: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tone": self.tone,
            "allow_aggressive_language": self.allow_aggressive_language,
            "forbidden_words": self.forbidden_words,
            "max_length": self.max_length,
            "min_length": self.min_length,
            "allow_hype": self.allow_hype,
        }


@dataclass
class HeadlineContext:
    article_id: str
    headline_text: str
    headline_block_id: str = ""
    kicker_text: str = ""
    subheadline_text: str = ""
    lead_text: str = ""
    body_summary: str = ""
    issue_tags: List[str] = field(default_factory=list)
    policy_constraints: Optional[PolicyConstraints] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "article_id": self.article_id,
            "headline_block_id": self.headline_block_id,
            "headline_text": self.headline_text,
            "kicker_text": self.kicker_text,
            "subheadline_text": self.subheadline_text,
            "lead_text": self.lead_text[:200] if len(self.lead_text) > 200 else self.lead_text,
            "body_summary": self.body_summary,
            "issue_tags": self.issue_tags,
            "policy_constraints": self.policy_constraints.to_dict() if self.policy_constraints else None,
        }
