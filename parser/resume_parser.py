# resume_parser.py
import re
from typing import Dict, List
from section.project_section import ProjectSection
from section.resume_section import ResumeSection

class ResumeParser:
    """简历解析器：将OCR文本转换为结构化的简历模块"""
    
    def __init__(self):
        # 标题映射：标准模块名 -> 多语言关键词变体
        self.SECTION_TITLES = {
        "personal_info": ["personal information", "contact", "基本信息", "联系方式"],
        "education": ["education", "education background", "academic history", "学历", "教育经历","教育背景"],
        "experience": ["work experience", "experience", "职业经历", "工作经历", "实习经历"],
        "projects": ["projects", "project experience", "项目", "项目经历"],
        "skills": ["skills", "technical skills", "技能", "技术"],
        "certifications": ["certifications", "certificates", "证书"],
        "languages": ["languages", "语言能力", "语言"]
    }

    def normalize_text(self, text: str) -> List[str]:
        """去除空行、首尾空格，按行分段"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines

    def detect_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        """根据标题识别各模块段落内容"""
        section_map = {}
        current_section = "personal_info"

        for line in lines:
            matched = False
            for tag, variants in self.SECTION_TITLES.items():
                for pattern in variants:
                    if re.match(rf"(?i)^.*{re.escape(pattern)}.*$", line):
                        current_section = tag
                        print(f"Matched section: {current_section} for line: {line}")
                        matched = True
                        break
                if matched:
                    break
            section_map.setdefault(current_section, []).append(line)

        return {k: "\n".join(v) for k, v in section_map.items()}

    def parse_resume(self, ocr_text: str) -> Dict[str, str]:
        """主接口函数：将OCR简历文本结构化为模块字典"""
        lines = self.normalize_text(ocr_text)
        sections = self.detect_sections(lines)
        
        
        return sections


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
    for section, content in structured.items():
        
        section = ResumeSection(name=section, raw_text=content)
        print(section.to_markdown())
        
        # if section == "projects":
        #     project_section = ProjectSection(name=section, raw_text=content)
        #     print(project_section.to_markdown())
        
        #print(f"\n== {section.upper()} ==\n{content}")