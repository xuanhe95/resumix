import streamlit as st
from utils.logger import logger
from parser.resume_parser import ResumeParser
from components.cards.score_card import display_score_card
import re
from typing import Dict
from section.section_base import SectionBase


def score_resume_section(section_name, content, jd_content, llm_model):
    logger.info(f"Scoring section: {section_name} with content length {len(content)}")
    """
    给简历段落打分，返回 dict 包含分数与评语。
    """

    prompt = f"""
        你是一位人力资源专家，请对以下简历段落进行打分和简要评语，满分为10分，维度如下：
        - 完整性：信息是否全面
        - 清晰度：表达是否清晰、条理清楚
        - 匹配度：与岗位描述是否贴合
        - 表达专业性：是否使用专业术语，表达是否得体
        - 成就导向：是否突出成就和贡献
        - 数据支撑：是否有量化的数据支持

        - 评语：请给出简要的评语，指出优点和改进建议。

        岗位描述：
            {jd_content}

        简历段落（{section_name}）：
            \"\"\"{content}\"\"\"

            请返回以下格式的内容：
                完整性: x
                清晰度: x
                匹配度: x
                表达专业性: x
                成就导向: x
                数据支撑: x
                评语: xxx
    """

    response = llm_model(prompt)

    result = {
        "完整性": 0,
        "清晰度": 0,
        "匹配度": 0,
        "表达专业性": 0,
        "成就导向": 0,
        "数据支撑": 0,
        "评语": "",
    }

    for key in result.keys():
        pattern = rf"{key}[:：]\s*(\d+|.+)"
        match = re.search(pattern, response)
        if match:
            if key != "评语":
                try:
                    result[key] = int(match.group(1))
                except:
                    result[key] = 0
            else:
                result[key] = match.group(1).strip()
    return result


def analyze_resume_with_scores(
    sections: Dict[str, SectionBase], jd_content: str, llm_model
):
    logger.info("开始简历评分分析...")

    total = len(sections)
    progress_bar = st.progress(0)

    for idx, section in enumerate(sections.values(), 1):
        with st.spinner(f"正在评分 {section.name}..."):
            scores = score_resume_section(
                section.name, section.raw_text, jd_content, llm_model
            )
            display_score_card(section.name, scores)
            st.markdown("---")

        progress_bar.progress(idx / total)

    st.success("所有简历段落评分完成 ✅")
