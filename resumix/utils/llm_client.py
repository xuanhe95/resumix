from uuid import UUID
import requests
import os
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from typing import Any, List, Optional, Dict
from pydantic import Field
from loguru import logger
from dotenv import load_dotenv
import hashlib
import base64
import time

from resumix.config.llm_config import LLMConfig

# Load environment variables
load_dotenv()

LLM_CONFIG = LLMConfig.get_config()


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
    _instance = None

    def __new__(cls, timeout=60):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        timeout=60,
    ):
        """
        初始化 LLM 客户端。

        参数：
            base_url: LLM 接口地址
            model_name: 模型名称
            timeout: 请求超时时间（秒）
        """
        if self._initialized:
            return
        self.base_url = LLM_CONFIG.get("url", None)
        self.model_name = LLM_CONFIG.get("model", "local_llm")
        self.api_key = LLM_CONFIG.get("api_key", None)
        self.timeout = timeout

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

    def _call_deepseek_api(self, prompt: str) -> str:
        api_key = LLM_CONFIG.get("api_key", None)

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        res = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        return (
            res.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "⚠️ Model did not return a result.")
        )

    def _call_local_llm(self, prompt: str) -> str:
        """
        调用本地 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的字符串或错误信息。
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }

        res = requests.post(
            self.base_url,
            json=payload,
            timeout=self.timeout,
        )

        return res.json().get("response", "⚠️ Model did not return a result.")

    def _call_teleai_api(self, prompt: str) -> str:

        account = LLM_CONFIG.get("username", "")
        timestamp = str(int(time.time()))
        secret = self.api_key

        raw_string = f"{account},{timestamp},{secret}"
        logger.info(f"Raw string for signature: {raw_string}")
        # 计算 SHA256 哈希
        sha256_hash = hashlib.sha256(raw_string.encode("utf-8")).digest()

        # Base64 编码
        signature = base64.b64encode(sha256_hash).decode("utf-8")
        logger.info(f"Generated signature: {signature}")

        headers = {
            "account": account,
            "time-stamp": str(int(time.time())),
            "authorization": signature,
            "apiKey": self.api_key,
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        }

        res = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        if not res.ok:
            return f"❌ Error: {res.status_code} - {res.text}"

        return (
            res.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "⚠️ Model did not return a result.")
        )

    def _call_silicon_api(self, prompt: str) -> requests.Response:
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 2000,
            "n": 1,
            "stop": [],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        res = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        if not res.ok:
            return f"❌ Error: {res.status_code} - {res.text}"

        return (
            res.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "⚠️ Model did not return a result.")
        )

    def generate(self, prompt: str) -> str:
        """
        调用 LLM 生成文本。

        参数：
            prompt: 输入提示文本

        返回：
            LLM 生成的        logger.info(f"Raw string for signature: {raw_string}")
                loger.ggger.info()                logger.info("Using DeepSeek API")
                logger.info()                logger.info("Using TeleAI API")
                logger.info()                logger.info("Using Local LLM")。
        """
        try:
            logger.info(f"Prompt Length: {len(prompt)}")

            if LLM_CONFIG.get("type") == "deepseek":
                logger.info("Using DeepSeek API")
                return self._call_deepseek_api(prompt)
            elif LLM_CONFIG.get("type") == "silicon":
                logger.info("Using Silicon API")
                return self._call_silicon_api(prompt)
            elif LLM_CONFIG.get("type") == "teleai":
                logger.info("Using TeleAI API")
                return self._call_teleai_api(prompt)
            else:
                logger.info("Using Local LLM")
                return self._call_local_llm(prompt)

        except Exception as e:
            return f"❌ Error calling model: {e}"
