from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

# Load env from standalone folder so config is stable regardless of invocation cwd.
load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)


@dataclass
class LLMConfig:
    provider: str
    url: str
    model: str
    timeout: int
    api_key: str = ""
    api_secret: str = ""


def load_llm_config() -> LLMConfig:
    provider = os.getenv("LLM_PROVIDER", "modal_openai").strip().lower()
    if provider == "local":
        return LLMConfig(
            provider="local",
            url=os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate"),
            model=os.getenv("LOCAL_LLM_MODEL", "gemma3:4b"),
            timeout=int(os.getenv("MODAL_TIMEOUT", "120")),
        )
    return LLMConfig(
        provider="modal_openai",
        url=os.getenv("MODAL_OPENAI_API_URL", "").strip(),
        model=os.getenv("MODAL_OPENAI_MODEL", "").strip(),
        timeout=int(os.getenv("MODAL_TIMEOUT", "120")),
        api_key=os.getenv("MODAL_API_KEY", "").strip(),
        api_secret=os.getenv("MODAL_API_SECRET", "").strip(),
    )


class LLMClient:
    """
    Keep structure consistent with existing project style:
    - __call__
    - generate
    - generate_json
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.cfg = config or load_llm_config()
        # Backward compatible:
        # - preferred: LLM_DEBUG_HTTP
        # - fallback: LLM_DEBUG
        debug_http_raw = os.getenv(
            "LLM_DEBUG_HTTP",
            os.getenv("LLM_DEBUG", "0"),
        ).strip().lower()
        self.debug_http = debug_http_raw in {"1", "true", "yes", "on"}
        if self.debug_http:
            print(
                f"[LLM DEBUG] provider={self.cfg.provider} url={self.cfg.url} model={self.cfg.model}",
                flush=True,
            )

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        hidden = {"modal-key", "modal-secret", "authorization", "x-api-key"}
        sanitized: Dict[str, str] = {}
        for k, v in headers.items():
            sanitized[k] = self._mask_secret(v) if k.lower() in hidden else v
        return sanitized

    def _debug_request(
        self, provider: str, url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> None:
        if not self.debug_http:
            return
        print(
            f"\n[LLM DEBUG][{provider}] HTTP request\n"
            f"url={url}\n"
            f"headers={json.dumps(self._sanitize_headers(headers), ensure_ascii=False)}\n"
            f"payload={json.dumps(payload, ensure_ascii=False)}\n",
            flush=True,
        )

    def _debug_response_error(self, provider: str, status: int, body: str) -> None:
        print(
            f"\n[LLM ERROR][{provider}] HTTP error status={status}\nbody={body}\n",
            flush=True,
        )

    def __call__(self, prompt: str) -> str:
        return self.generate(prompt)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Modal-Key"] = self.cfg.api_key
        if self.cfg.api_secret:
            headers["Modal-Secret"] = self.cfg.api_secret
        return headers

    def _call_local(self, prompt: str) -> str:
        payload = {"model": self.cfg.model, "prompt": prompt, "stream": False}
        headers = {"Content-Type": "application/json"}
        self._debug_request("local", self.cfg.url, headers, payload)
        r = requests.post(self.cfg.url, json=payload, headers=headers, timeout=self.cfg.timeout)
        if not r.ok:
            self._debug_response_error("local", r.status_code, r.text)
            return f"❌ Error: {r.status_code} - {r.text}"
        return r.json().get("response", "")

    def _call_modal_openai(self, prompt: str, force_json: bool = False) -> str:
        if (
            not self.cfg.url
            or "your-modal-openai-endpoint" in self.cfg.url
            or "your-modal-endpoint" in self.cfg.url
        ):
            return "❌ Error: MODAL_OPENAI_API_URL is not configured with a real endpoint."

        payload: Dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 1400,
            "temperature": 0.1 if force_json else 0.2,
            "top_p": 0.9,
        }
        if force_json:
            payload["response_format"] = {"type": "json_object"}
        headers = self._headers()
        self._debug_request("modal_openai", self.cfg.url, headers, payload)
        r = requests.post(
            self.cfg.url,
            json=payload,
            headers=headers,
            timeout=self.cfg.timeout,
        )
        if not r.ok:
            self._debug_response_error("modal_openai", r.status_code, r.text)
            return f"❌ Error: {r.status_code} - {r.text}"
        data = r.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

    def generate(self, prompt: str) -> str:
        if self.cfg.provider == "local":
            return self._call_local(prompt)
        return self._call_modal_openai(prompt, force_json=False)

    def generate_json(self, prompt: str) -> str:
        if self.cfg.provider == "modal_openai":
            return self._call_modal_openai(prompt, force_json=True)
        strict_prompt = "Return valid JSON only.\n\n" + prompt
        return self._call_local(strict_prompt)
