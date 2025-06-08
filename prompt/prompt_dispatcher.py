# dispatcher/prompt_dispatcher.py
from prompt.prompt_templates import PROMPT_MAP
from section.section_base import SectionBase


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

    def get_tailoring_prompt(self, full_cv: str) -> str:
        """
        用于整体润色的 prompt 构造
        """
        prompt = self.prompt_templates["tailor"]
        return prompt.replace("<CV_TEXT>", full_cv.strip())
