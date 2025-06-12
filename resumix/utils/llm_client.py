from uuid import UUID
import requests
import os
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from typing import Any, List, Optional, Dict
from pydantic import Field
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMWrapper(BaseLLM):
    client: Any = Field(exclude=True)
    model_name: str = "local_llm"

    # 兼容 LangChain Agent 的必要字段
    callbacks: Optional[List[Any]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        调用 LLM 生成文本。

        参数：
            prompt: 输入提示文本
            stop: 可选的停止符列表

        返回：
            LLM 生成的字符串。
        """
        logger.info(f"Calling LLM with prompt: {prompt[:50]}...")
        return self.client(prompt)

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型"""
        return "llm"

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
        初始化 LLM 客户端。

        参数：
            base_url: LLM 接口地址
            model_name: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.is_local = "localhost" in base_url or "127.0.0.1" in base_url
        logger.info(f"Initialized {model_name} on {base_url} (Local: {self.is_local})")

    def __call__(self, prompt: str) -> str:
        """
        调用 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的字符串或错误信息。
        """
        logger.info(f"Calling: {prompt[:50]}")
        return self.generate(prompt)

    def generate(self, prompt: str) -> str:
        """
        调用 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的字符串或错误信息。
        """
        try:
            logger.info(f"Prompt Length: {len(prompt)}")
            
            if self.is_local:
                # Local LLM format
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                }
            else:
                # API format (Deepseek)
                api_key = os.getenv("DEEPSEEK_API_KEY")
                if not api_key:
                    raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            
            res = requests.post(
                self.base_url,
                json=payload,
                headers=headers if not self.is_local else None,
                timeout=self.timeout,
            )
            
            if not res.ok:
                return f"❌ Error: {res.status_code} - {res.text}"
                
            if self.is_local:
                return res.json().get("response", "⚠️ Model did not return a result.")
            else:
                return res.json().get("choices", [{}])[0].get("message", {}).get("content", "⚠️ Model did not return a result.")
                
        except Exception as e:
            return f"❌ Error calling model: {e}"
