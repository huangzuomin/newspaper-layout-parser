"""
LLM-backed candidate generator for executive optimization tasks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OptimizationLLMGenerator:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.raw_config = config
        self.config = config.get("optimization_generation", config)
        self.enabled = self.config.get("enabled", False)
        self.provider = str(self.config.get("provider", "anthropic")).lower()
        self.api_key = self.config.get("api_key") or os.getenv(
            self.config.get("api_key_env", "ANTHROPIC_API_KEY")
        )
        self.model = self.config.get("model", "claude-3-5-sonnet-20241022")
        self.timeout_seconds = int(self.config.get("timeout_seconds", 30))
        self.temperature = float(self.config.get("temperature", 0.2))
        self.base_url = self.config.get("base_url", "").strip()
        self.max_options_per_task = int(self.config.get("max_options_per_task", 3))
        self.prompt_template = self._load_prompt_template()

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key and self.model)

    def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Optimization LLM generator is not enabled")

        prompt = self._build_prompt(payload)
        if self.provider == "openai":
            text = self._call_openai(prompt)
        else:
            text = self._call_anthropic(prompt)
        return self._parse_response(text)

    def _load_prompt_template(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "optimizer_prompt.md"
        return prompt_path.read_text(encoding="utf-8")

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            f"{self.prompt_template.strip()}\n\n"
            "请只输出一个 JSON 对象，不要输出任何额外说明。\n\n"
            f"输入数据:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _call_anthropic(self, prompt: str) -> str:
        request = Request(
            self.base_url or "https://api.anthropic.com/v1/messages",
            data=json.dumps(
                {
                    "model": self.model,
                    "max_tokens": 1400,
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

    def _call_openai(self, prompt: str) -> str:
        request = Request(
            self.base_url or "https://api.openai.com/v1/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "temperature": self.temperature,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是总编辑优化助手，只能输出 JSON。",
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
            raise RuntimeError("OpenAI response missing choices")
        return choices[0].get("message", {}).get("content", "").strip()

    def _parse_response(self, text: str) -> Dict[str, Any]:
        if not text:
            raise RuntimeError("LLM returned empty content")
        parsed = json.loads(self._extract_json_object(text))
        if not isinstance(parsed.get("options"), list):
            raise RuntimeError("LLM response missing options")
        parsed["options"] = parsed["options"][: self.max_options_per_task]
        return parsed

    @staticmethod
    def _extract_json_object(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("LLM response does not contain a JSON object")
        return text[start : end + 1]
