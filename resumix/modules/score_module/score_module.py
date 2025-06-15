from resumix.prompt.prompt_dispatcher import PromptDispatcher
from resumix.section.section_base import SectionBase
from resumix.utils.llm_client import LLMClient
from resumix.utils.logger import logger
from typing import Dict
import streamlit as st
from resumix.components.cards.score_card import display_score_card
from resumix.utils.json_parser import JsonParser


class ScoreModule:
    def __init__(self):
        """
        初始化评分模块。

        参数：
            llm: LLM 客户端实例
        """
        self.llm = LLMClient()
        self.prompt_dispatcher = PromptDispatcher()

    def score_resume(
        self,
        resume_section: SectionBase,
        jd_section_basic: SectionBase,
        jd_section_preferred: SectionBase,
    ) -> dict:
        """
        根据简历和岗位描述评分。

        返回：
            评分结果字典（包括 relevance, coverage 等指标）
        """
        prompt = self.prompt_dispatcher.get_score_prompt(
            resume_section, jd_section_basic, jd_section_preferred
        )

        response = self.llm(prompt=prompt)

        logger.debug(f"Score prompt: {prompt}")
        logger.debug(f"Score response: {response}")

        try:
            result = JsonParser.parse(response)
            assert isinstance(result, dict)
            return result
        except Exception as e:
            logger.warning(
                f"[ScoreModule] LLM 评分结果解析失败: {e}, 原始响应: {response}"
            )
            return {"error": "无法解析评分结果", "raw": response}


if __name__ == "__main__":
    score_module = ScoreModule()

    # 示例简历和岗位描述
    resume_section = SectionBase(name="experience", raw_text="工作经历示例文本")
    jd_section_basic = SectionBase(name="basic", raw_text="岗位基本要求示例文本")
    jd_section_preferred = SectionBase(
        name="preferred", raw_text="岗位优先条件示例文本"
    )

    score_result = score_module.score_resume(
        resume_section, jd_section_basic, jd_section_preferred
    )
    print(score_result)
