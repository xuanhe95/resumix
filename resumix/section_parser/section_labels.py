# section_labels.py

from typing import Dict, List, Union


class SectionLabels:
    """封装多语言简历段落标签及关键词匹配"""

    # 支持的语言版本
    SUPPORTED_LANGUAGES = ["en", "zh"]

    # 标签映射（中英文）
    LABELS: Dict[str, Dict[str, List[str]]] = {
        "zh": {
            "personal_info": [
                "个人信息",
                "联系方式",
                "基本信息",
                "电话",
                "邮箱",
                "地址",
                "GitHub",
                "LinkedIn",
                "姓名",
                "出生日期",
                "籍贯",
            ],
            "education": [
                "教育背景",
                "教育经历",
                "学历",
                "毕业院校",
                "学位",
                "主修课程",
            ],
            "experience": [
                "工作经历",
                "职业经历",
                "实习经历",
                "项目经验",
                "实习岗位",
                "全职工作",
            ],
            "projects": ["项目经历", "个人项目", "项目经验", "开发项目", "工程实践"],
            "skills": ["技能", "专业技能", "语言能力", "编程语言", "技术栈"],
            "awards": ["证书", "奖项", "荣誉", "竞赛获奖", "资格认证"],
        },
        "en": {
            "personal_info": [
                "personal information",
                "contact",
                "name",
                "phone",
                "email",
                "address",
                "github",
                "linkedin",
                "birth",
                "location",
            ],
            "education": [
                "education",
                "education background",
                "degree",
                "school",
                "university",
                "major",
                "gpa",
            ],
            "experience": [
                "work experience",
                "internship",
                "career",
                "employment",
                "job",
                "full-time",
            ],
            "projects": [
                "projects",
                "project experience",
                "personal projects",
                "software project",
            ],
            "skills": [
                "skills",
                "technical skills",
                "programming",
                "languages",
                "competencies",
                "proficiencies",
            ],
            "awards": ["awards", "certificates", "honors", "achievements"],
        },
    }

    @classmethod
    def get_labels(
        cls, langs: Union[str, List[str]] = ["zh", "en"]
    ) -> Dict[str, List[str]]:
        """
        获取指定语言下的标签字典。
        - 支持传入单个语言（str）或多个语言列表（List[str]）
        - 多语言时，返回合并后的标签，自动去重
        """
        if isinstance(langs, str):
            return cls.LABELS.get(langs, {})

        # 合并多个语言下的标签
        merged = {}
        for lang in langs:
            lang_dict = cls.LABELS.get(lang, {})
            for tag, values in lang_dict.items():
                merged.setdefault(tag, []).extend(values)

        # 对每个标签值去重
        return {tag: list(set(vals)) for tag, vals in merged.items()}

    @classmethod
    def get_flat_labels(cls, lang: str = "zh") -> Dict[str, List[str]]:
        """返回平展结构，用于模型 encode，例如 {'skills': ['技能', '技术', ...]}"""
        return cls.get_labels(lang)

    @classmethod
    def get_all_keywords(cls, lang: str = "zh") -> List[str]:
        """返回所有标签下的关键词集合"""
        all_labels = cls.get_labels(lang)
        return [kw for keywords in all_labels.values() for kw in keywords]

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        return cls.SUPPORTED_LANGUAGES
