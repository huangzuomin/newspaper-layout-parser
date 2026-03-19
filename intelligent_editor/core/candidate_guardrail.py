"""
Simple guardrails for rewrite options shown to editors.
"""

from __future__ import annotations

from typing import Iterable, List


class CandidateGuardrail:
    def __init__(self, max_length: int = 26):
        self.max_length = max_length
        self.forbidden_terms = ["最强", "震惊", "爆款", "必须看", "曝光"]

    def allow(self, text: str) -> bool:
        if not text:
            return False
        if len(text) > self.max_length:
            return False
        if any(term in text for term in self.forbidden_terms):
            return False
        return True

    def filter(self, candidates: Iterable[str]) -> List[str]:
        return [item for item in candidates if self.allow(item)]
