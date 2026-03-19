"""
Layered executive report models for the redesigned editor workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EngineeringBaselineFinding:
    severity: str
    summary: str
    action: str
    source: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "summary": self.summary,
            "action": self.action,
            "source": self.source,
        }


@dataclass
class EngineeringBaselineReport:
    status: str
    finding_count: int
    findings: List[EngineeringBaselineFinding] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "finding_count": self.finding_count,
            "findings": [item.to_dict() for item in self.findings],
            "note": self.note,
        }


@dataclass
class SafetyFinding:
    level: str
    title: str
    detail: str
    action: str
    source: str
    requires_manual_review: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "title": self.title,
            "detail": self.detail,
            "action": self.action,
            "source": self.source,
            "requires_manual_review": self.requires_manual_review,
        }


@dataclass
class SafetyReport:
    recommendation: str
    risk_level: str
    summary: str
    findings: List[SafetyFinding] = field(default_factory=list)
    semantic_review_enabled: bool = False
    requires_manual_review: bool = True
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "risk_level": self.risk_level,
            "summary": self.summary,
            "findings": [item.to_dict() for item in self.findings],
            "semantic_review_enabled": self.semantic_review_enabled,
            "requires_manual_review": self.requires_manual_review,
            "note": self.note,
        }


@dataclass
class OptimizationOption:
    label: str
    content: str
    rationale: str
    fit_for: str
    source: str = "rule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "content": self.content,
            "rationale": self.rationale,
            "fit_for": self.fit_for,
            "source": self.source,
        }


@dataclass
class OptimizationTask:
    id: str
    priority: str
    title: str
    why_it_matters: str
    task_type: str
    article_ids: List[str] = field(default_factory=list)
    options: List[OptimizationOption] = field(default_factory=list)
    source: str = "hybrid"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "priority": self.priority,
            "title": self.title,
            "why_it_matters": self.why_it_matters,
            "task_type": self.task_type,
            "article_ids": self.article_ids,
            "options": [item.to_dict() for item in self.options],
            "source": self.source,
        }


@dataclass
class OptimizationReport:
    summary: str
    tasks: List[OptimizationTask] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "tasks": [item.to_dict() for item in self.tasks],
            "note": self.note,
        }


@dataclass
class ExecutiveAuditReport:
    executive_summary: Dict[str, Any]
    safety_report: SafetyReport
    optimization_report: OptimizationReport
    engineering_baseline: EngineeringBaselineReport
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive_summary": self.executive_summary,
            "safety_report": self.safety_report.to_dict(),
            "optimization_report": self.optimization_report.to_dict(),
            "engineering_baseline": self.engineering_baseline.to_dict(),
            "metadata": self.metadata,
        }
