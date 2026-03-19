"""
LLM enhanced headline generator with provider-compatible HTTP calls.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models.headline_rewrite import (
    HeadlineContext,
    RewriteCandidate,
    RewriteStyle,
    RiskLevel,
)

logger = logging.getLogger("intelligent_editor")


class LLMEnhancedGenerator:
    """Generate headline rewrite candidates through a configurable compatible API."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.provider = str(self.config.get("provider", "openai")).lower()
        self.api_key = self.config.get("api_key") or os.getenv(
            self.config.get("api_key_env", "ARK_API_KEY")
        )
        self.model = self.config.get("model", "kimi-k2.5")
        self.base_url = self.config.get(
            "base_url", "https://ark.cn-beijing.volces.com/api/coding/v3"
        )
        self.temperature = float(self.config.get("temperature", 0.2))
        self.timeout_seconds = int(self.config.get("timeout_seconds", 30))

        if not self.api_key:
            logger.warning("LLM headline generator API key not set, generation disabled")
            self.enabled = False

        if self.enabled:
            logger.info(
                "LLMEnhancedGenerator initialized with provider=%s model=%s",
                self.provider,
                self.model,
            )
        else:
            logger.info("LLMEnhancedGenerator disabled")

    def generate_with_llm(
        self,
        context: HeadlineContext,
        target_style: RewriteStyle,
        num_variations: int = 1,
    ) -> List[RewriteCandidate]:
        if not self.enabled:
            logger.info("LLM generation disabled, skipping")
            return []

        try:
            prompt = self._build_prompt(context, target_style, num_variations)
            if self.provider == "anthropic":
                content = self._call_anthropic(prompt)
            else:
                content = self._call_openai(prompt)
            candidates = self._parse_llm_response(content, target_style)
            logger.info("LLM generated %s headline candidates", len(candidates))
            return candidates
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return []

    def _build_prompt(
        self,
        context: HeadlineContext,
        target_style: RewriteStyle,
        num_variations: int,
    ) -> str:
        style_desc = {
            RewriteStyle.CONSERVATIVE: "稳妥版，尽量贴近原稿气质，安全边界最优先",
            RewriteStyle.FOCUSED: "聚焦版，突出动作、结果、对象，提高信息密度",
            RewriteStyle.PEOPLE_ORIENTED: "民生版，强调群众感受和现实落点，但不口语化",
        }

        lines = [
            "你是一名专业报纸标题编辑。",
            f"请生成 {num_variations} 个{style_desc[target_style]}标题。",
            f"原标题：{context.headline_text}",
        ]
        if context.kicker_text:
            lines.append(f"栏题/引题：{context.kicker_text}")
        if context.subheadline_text:
            lines.append(f"副题：{context.subheadline_text}")
        if context.lead_text:
            lines.append(f"导语片段：{context.lead_text[:100]}")
        if context.body_summary:
            lines.append(f"正文摘要：{context.body_summary[:180]}")
        if context.issue_tags:
            lines.append(f"已识别问题：{', '.join(context.issue_tags)}")

        lines.extend(
            [
                "约束：",
                "1. 不得改变事实。",
                "2. 不得改变政治口径。",
                "3. 不得添加正文没有的新信息。",
                "4. 禁止使用夸张、营销化、网络化表达。",
                "5. 标题尽量控制在 12 到 20 字，最多不超过 26 字。",
                "输出要求：",
                "1. 每行一个标题。",
                "2. 使用“1. 标题”这种格式。",
                "3. 不要输出解释。",
            ]
        )
        return "\n".join(lines)

    def _call_openai(self, prompt: str) -> str:
        request = Request(
            self.base_url,
            data=json.dumps(
                {
                    "model": self.model,
                    "temperature": self.temperature,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是报纸标题改写助手，只输出编号标题列表。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        return self._read_response(request, anthropic=False)

    def _call_anthropic(self, prompt: str) -> str:
        request = Request(
            self.base_url,
            data=json.dumps(
                {
                    "model": self.model,
                    "max_tokens": 1000,
                    "temperature": self.temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        return self._read_response(request, anthropic=True)

    def _read_response(self, request: Request, anthropic: bool) -> str:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"LLM network error: {exc}") from exc

        if anthropic:
            parts = payload.get("content", [])
            return "\n".join(
                item.get("text", "") for item in parts if item.get("type") == "text"
            ).strip()

        choices = payload.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI-compatible response missing choices")
        return choices[0].get("message", {}).get("content", "").strip()

    def _parse_llm_response(
        self,
        content: str,
        target_style: RewriteStyle,
    ) -> List[RewriteCandidate]:
        candidates: List[RewriteCandidate] = []
        version = 1

        for raw_line in content.strip().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.match(r"^\d+\.", line):
                line = line.split(".", 1)[1].strip()
            if len(line) < 6 or len(line) > 26:
                continue

            is_safe, risk_reasons = self._check_llm_generated_risk(line)
            risk_level = RiskLevel.SAFE if is_safe else RiskLevel.USABLE_WITH_REVIEW
            risk_note = "稳妥" if is_safe else "需审看：" + "；".join(risk_reasons)

            candidates.append(
                RewriteCandidate(
                    version=version,
                    headline=line,
                    style=target_style,
                    changes="LLM 生成，基于上下文与约束优化",
                    risk_note=risk_note,
                    risk_level=risk_level,
                    confidence=0.7,
                    source="llm",
                )
            )
            version += 1

        return candidates

    def _check_llm_generated_risk(self, headline: str) -> tuple[bool, List[str]]:
        risk_reasons: List[str] = []
        is_safe = True

        forbidden_words = ["震惊", "重磅", "最强", "必看", "曝光"]
        for word in forbidden_words:
            if word in headline:
                risk_reasons.append(f"包含禁用词：{word}")
                is_safe = False

        net_speak_patterns = [
            r"惊艳",
            r"刷屏",
            r"网红",
            r"流量",
            r"爆款",
            r"必火",
            r"疯传",
        ]
        for pattern in net_speak_patterns:
            if re.search(pattern, headline):
                risk_reasons.append("可能包含网络化表达")
                is_safe = False
                break

        if "!" in headline or "！" in headline:
            risk_reasons.append("包含感叹号，可能过于情绪化")
            is_safe = False

        return is_safe, risk_reasons

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key)
