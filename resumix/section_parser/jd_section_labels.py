# jd_section_labels.py

from typing import Dict, List, Union


class JDSectionLabels:
    """封装多语言 JD 段落标签及关键词匹配"""

    SUPPORTED_LANGUAGES = ["en", "zh"]

    LABELS: Dict[str, Dict[str, List[str]]] = {
        "zh": {
            "overview": ["职位描述", "岗位介绍", "组织介绍", "职位信息", "职位概况"],
            "responsibilities": ["岗位职责", "工作内容", "日常任务", "工作职责"],
            "requirements_basic": [
                "岗位要求",
                "任职要求",
                "基本要求",
                "资质要求",
                "能力要求",
            ],
            "requirements_preferred": ["优先条件", "加分项", "附加要求", "期望条件"],
            # "team_culture": ["团队文化", "工作氛围", "包容文化", "价值观"],
            # "growth": ["职业发展", "晋升空间", "成长路径", "学习机会"],
            "location": [
                "地点",
                "办公地点",
            ],
            "salary": [
                "薪资",
                "薪酬",
                "工资",
                "薪资范围",
                "薪资待遇",
                "薪资福利",
                "薪资结构",
                "薪资水平",
            ],
        },
        "en": {
            "overview": [
                "job description",
                "about the team",
                "position summary",
                "role overview",
            ],
            "responsibilities": [
                "responsibilities",
                "key job responsibilities",
                "duties",
                "what you will do",
            ],
            "requirements_basic": [
                "basic qualifications",
                "required qualifications",
                "requirements",
            ],
            "requirements_preferred": [
                "preferred qualifications",
                "nice to have",
                "bonus skills",
            ],
            # "team_culture": [
            #     "team culture",
            #     "inclusive culture",
            #     "company values",
            #     "diversity and inclusion",
            # ],
            # "growth": [
            #     "mentorship",
            #     "career growth",
            #     "learning opportunities",
            #     "career development",
            # ],
            "location": [
                "location",
                "office location",
                "workplace",
            ],
            "salary": [
                "salary",
                "compensation",
                "pay",
                "base pay",
                "salary range",
                "benefits",
            ],
        },
    }

    @classmethod
    def get_labels(
        cls, langs: Union[str, List[str]] = ["zh", "en"]
    ) -> Dict[str, List[str]]:
        if isinstance(langs, str):
            return cls.LABELS.get(langs, {})

        merged = {}
        for lang in langs:
            lang_dict = cls.LABELS.get(lang, {})
            for tag, values in lang_dict.items():
                merged.setdefault(tag, []).extend(values)

        return {tag: list(set(vals)) for tag, vals in merged.items()}

    @classmethod
    def get_flat_labels(cls, lang: str = "zh") -> Dict[str, List[str]]:
        return cls.get_labels(lang)

    @classmethod
    def get_all_keywords(cls, lang: str = "zh") -> List[str]:
        all_labels = cls.get_labels(lang)
        return [kw for keywords in all_labels.values() for kw in keywords]

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        return cls.SUPPORTED_LANGUAGES
