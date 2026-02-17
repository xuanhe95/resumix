from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from pydantic import Field


class LLMWrapper(BaseLLM):
    client: Any = Field(exclude=True)
    model_name: str = "resume_agent_llm"
    callbacks: Optional[List[Any]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        return self.client(prompt)

    @property
    def _llm_type(self) -> str:
        return "resume_agent_llm"

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResult:
        generations = [[Generation(text=self._call(p))] for p in prompts]
        return LLMResult(generations=generations)

