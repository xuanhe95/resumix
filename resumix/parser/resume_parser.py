from typing import Dict, List, Union
import re

from section.education_section import EducationSection
from section.experience_section import ExperienceSection
from section.info_section import PersonalInfoSection
from section.projects_section import ProjectsSection
from section.skills_section import SkillsSection
from section.section_base import SectionBase

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SECTIONS = {
    "personal_info": PersonalInfoSection,
    "education": EducationSection,
    "experience": ExperienceSection,
    "projects": ProjectsSection,
    "skills": SkillsSection,
}


class ResumeParser:
    def __init__(self):
        self.SECTION_TITLES = {
            "personal_info": [
                "personal information",
                "contact",
                "基本信息",
                "联系方式",
            ],
            "education": [
                "education",
                "education background",
                "academic history",
                "学历",
                "教育经历",
                "教育背景",
            ],
            "experience": [
                "work experience",
                "experience",
                "职业经历",
                "工作经历",
                "实习经历",
            ],
            "projects": ["projects", "project experience", "项目", "项目经历"],
            "skills": ["skills", "technical skills", "技能", "技术"],
        }

    def normalize_text(self, text: str, keep_blank: bool = False) -> List[str]:
        lines = text.splitlines()
        return [
            line.strip() if keep_blank else line.strip()
            for line in lines
            if keep_blank or line.strip()
        ]

    def detect_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        section_map = {}
        current_section = "personal_info"

        for line in lines:
            matched = False
            for tag, variants in self.SECTION_TITLES.items():
                for pattern in variants:
                    if re.match(rf"(?i)^.*{re.escape(pattern)}.*$", line):
                        current_section = tag
                        matched = True
                        break
                if matched:
                    break
            section_map.setdefault(current_section, []).append(line or "")

        return section_map

    def parse_resume(self, ocr_text: str) -> Dict[str, SectionBase]:
        lines = self.normalize_text(ocr_text, keep_blank=True)
        section_lines = self.detect_sections(lines)

        structured_sections = {}
        for section, line_list in section_lines.items():
            raw_text = "\n".join(line_list)  # 每个 Section 内部仍使用文本传入
            cls = SECTIONS.get(section)
            if cls:
                section_obj = cls(section, raw_text)
                section_obj.original_lines = line_list  # ✅ 保留原始行结构，供展示/分析
                section_obj.parse()
                structured_sections[section] = section_obj
            else:
                fallback = SectionBase(section, raw_text)
                fallback.original_lines = line_list
                fallback.parsed_data = {"raw": raw_text}
                structured_sections[section] = fallback

        return structured_sections


if __name__ == "__main__":
    sample_text = """
    张三
    电话: 123456789
    邮箱: zhangsan@example.com

    教育背景
    2015-2019 清华大学 计算机科学与技术 本科

    项目经历
    2020 OCR智能识别系统开发
    - 提高图像识别精度15%
    

    技能
    Python, PyTorch, Docker
    """

    parser = ResumeParser()

    structured = parser.parse_resume(sample_text)
    print(len(structured))

    for section, obj in structured.items():
        print(f"Section: {section}")
        print(obj.parsed_data)
        print(type(obj))
