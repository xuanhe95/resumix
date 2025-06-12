# dispatcher/prompt_dispatcher.py
from resumix.prompt.prompt_templates import PROMPT_MAP, SCORE_PROMPT_MAP
from resumix.section.section_base import SectionBase


class PromptDispatcher:
    """
    将结构化 Section 转换为对应的 Prompt
    """

    def __init__(self):
        self.prompt_templates = PROMPT_MAP

    def get_prompt(self, section: SectionBase, mode: str = "default") -> str:
        """
        根据 section 名称选取 prompt，并将 raw_text 插入 <CV_TEXT>
        """
        prompt = self.prompt_templates.get(section.name)
        if not prompt and mode != "tailor":
            raise ValueError(f"No prompt found for section: {section.name}")

        placeholder = "<CV_TEXT>"
        return prompt.replace(placeholder, section.raw_text.strip())

    def get_score_prompt(
        self,
        section: SectionBase,
        jd_section_basic: SectionBase,
        jd_section_preferred: SectionBase,
    ) -> str:
        """
        用于评分的 prompt 构造
        """
        prompt = SCORE_PROMPT_MAP[section.name]
        placeholder = "<CV_TEXT>"
        jd_basic_placeholder = "<JD_BASIC_TEXT>"
        jd_preferred_placeholder = "<JD_PREFERRED_TEXT>"

        # 替换 CV 和 JD 的占位符
        prompt = prompt.replace(placeholder, section.raw_text.strip())

        prompt = prompt.replace(jd_basic_placeholder, jd_section_basic.raw_text.strip())

        if jd_section_preferred:
            prompt = prompt.replace(
                jd_preferred_placeholder, jd_section_preferred.raw_text.strip()
            )

        return prompt

    def get_tailoring_prompt(self, full_cv: str) -> str:
        """
        用于整体润色的 prompt 构造
        """
        prompt = self.prompt_templates["tailor"]
        return prompt.replace("<CV_TEXT>", full_cv.strip())
