from typing import Dict
from loguru import logger
from prompt.prompt_dispatcher import PromptDispatcher
from section.section_base import SectionBase


class ResumeRewriter:
    def __init__(self, llm):
        self.llm = llm  # callable like: lambda prompt -> str
        self.dispatcher = PromptDispatcher()

    def rewrite_section(self, section: SectionBase, jd_text: str = "") -> SectionBase:
        # 获取针对该 section 的 prompt
        prompt = self.dispatcher.get_prompt(section)
        logger.info(f"Rewriting section '{section.name}' with LLM...")

        # 调用 LLM 接口
        rewritten_text = self.llm(prompt)

        # 写入回 section 对象
        section.rewritten_text = rewritten_text.strip()

    def rewrite_all(
        self, sections: Dict[str, SectionBase], jd_text: str = ""
    ) -> Dict[str, SectionBase]:
        rewritten = {}
        for name, section in sections.items():
            rewritten[name] = self.rewrite_section(section, jd_text)
        return rewritten
