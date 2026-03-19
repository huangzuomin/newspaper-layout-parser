"""
LLM-backed semantic safety reviewer for executive publishing decisions.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("intelligent_editor")


class SemanticSafetyReviewer:
    """Call an LLM provider and request structured safety findings."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.enabled = config.get("enabled", False)
        self.provider = str(config.get("provider", "anthropic")).lower()
        self.api_key = config.get("api_key") or os.getenv(
            config.get("api_key_env", "ANTHROPIC_API_KEY")
        )
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.temperature = float(config.get("temperature", 0.1))
        self.base_url = config.get("base_url", "").strip()
        self.prompt_template = self._load_prompt_template()

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key and self.model)

    def review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Semantic safety reviewer is not enabled")

        prompt = self._build_prompt(payload)
        if self.provider == "openai":
            response_text = self._call_openai(prompt)
        else:
            response_text = self._call_anthropic(prompt)
        return self._parse_response(response_text)

    def _load_prompt_template(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "safety_prompt.md"
        return prompt_path.read_text(encoding="utf-8")

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            f"{self.prompt_template.strip()}\n\n"
            "请只输出一个 JSON 对象，不要输出任何额外解释。\n\n"
            f"输入数据:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _call_anthropic(self, prompt: str) -> str:
        url = self.base_url or "https://api.anthropic.com/v1/messages"
        request_body = {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        request = Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        return self._read_response(request, anthropic=True)

    def _call_openai(self, prompt: str) -> str:
        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        request_body = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "你是报纸总编辑安全审校助手，只能输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
        }
        request = Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        return self._read_response(request, anthropic=False)

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
            text_parts = [item.get("text", "") for item in parts if item.get("type") == "text"]
            return "\n".join(part for part in text_parts if part).strip()

        choices = payload.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI response missing choices")
        return choices[0].get("message", {}).get("content", "").strip()

    def _parse_response(self, text: str) -> Dict[str, Any]:
        if not text:
            raise RuntimeError("LLM returned empty content")

        parsed = json.loads(self._extract_json_object(text))
        findings = parsed.get("findings")
        if not isinstance(findings, list):
            raise RuntimeError("LLM response missing findings list")
        return parsed

    @staticmethod
    def _extract_json_object(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("LLM response does not contain a JSON object")
        return text[start : end + 1]
