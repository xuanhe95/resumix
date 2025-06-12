import json
import re
from typing import Union, Dict
from loguru import logger


class JsonParser:
    @staticmethod
    def parse(response: str) -> Union[Dict, None]:
        """
        安全解析 LLM 响应中的 JSON 字符串。

        支持如下格式：
        1. 标准 JSON：{"a": 1}
        2. 带 markdown 代码块的 JSON：```json\n{...}\n```

        如果无法解析，返回 None。
        """

        if not isinstance(response, str):
            logger.warning("LLM 响应不是字符串")
            return None

        # 提取 json 块
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(pattern, response, re.DOTALL)
        cleaned = match.group(1) if match else response.strip()

        # 替换中文引号和奇怪字符为合法形式
        replacements = {
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "…": "...",
        }
        for bad, good in replacements.items():
            cleaned = cleaned.replace(bad, good)

        # 去除非法控制字符
        cleaned = re.sub(r"[\x00-\x1F\x7F]", "", cleaned)

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(
                f"[safe_json_parse] JSON 解析失败: {e}, 原始响应: {response}"
            )
            return None
