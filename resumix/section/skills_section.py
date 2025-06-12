import re
from resumix.section.section_base import SectionBase


class SkillsSection(SectionBase):
    def parse(self):
        lines = self.raw_text.splitlines()
        skills = []
        for line in lines:
            skills.extend(re.split(r"[，,;；]", line))
        self.parsed_data = [s.strip() for s in skills if s.strip()]
