from uuid import UUID
import requests
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from typing import Any, List, Optional, Dict
from pydantic import Field
from loguru import logger


class LLMWrapper(BaseLLM):
    client: Any = Field(exclude=True)
    model_name: str = "local_llm"

    # 兼容 LangChain Agent 的必要字段
    callbacks: Optional[List[Any]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        调用本地 LLM 生成文本。

        参数：
            prompt: 输入提示文本
            stop: 可选的停止符列表

        返回：
            LLM 生成的字符串。
        """

        logger.info(f"Calling local LLM with prompt: {prompt[:50]}...")
        return self.client(prompt)

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型"""
        return "local_llm"

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ) -> LLMResult:
        """
        批量生成文本（Agent 使用）
        """
        generations = [[Generation(text=self._call(p))] for p in prompts]
        return LLMResult(generations=generations)


class LLMClient:
    def __init__(
        self,
        base_url,
        model_name,
        timeout=60,
    ):
        """
        初始化本地 LLM 客户端。

        参数：
            base_url: 本地 LLM 接口地址
            model_name: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        logger.info(f"Initialized {model_name} on {base_url}")

    def __call__(self, prompt: str) -> str:
        """
        调用本地 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的字符串或错误信息。
        """
        logger.info(f"Calling: {prompt[:50]}")
        return self.generate(prompt)

    def generate(self, prompt: str) -> str:
        """
        调用本地 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的字符串或错误信息。
        """
        try:
            logger.info(f"Prompt Length: {len(prompt)}")
            res = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            return res.json().get("response", "⚠️ Model did not return a result.")
        except Exception as e:
            return f"❌ Error calling local model: {e}"
