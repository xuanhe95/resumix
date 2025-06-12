import streamlit as st
from utils.logger import logger
from components.cards.score_card import display_score_card
import re
from typing import Dict
from resumix.section.section_base import SectionBase
from resumix.modules.score_module.score_module import ScoreModule


def analyze_resume_with_scores(
    sections: Dict[str, SectionBase], jd_sections: Dict[str, SectionBase]
):
    logger.info("开始简历评分分析...")

    score_module = ScoreModule()

    total = len(sections)
    progress_bar = st.progress(0)

    if "requirements_basic" not in jd_sections:
        st.warning(
            "❗岗位描述缺少关键字段（requirements_basic / requirements_preferred），无法进行评分分析。"
        )
        return

    for idx, section in enumerate(sections.values(), 1):
        with st.spinner(f"正在评分 {section.name}..."):
            score = score_module.score_resume(
                section,
                jd_sections["requirements_basic"],
                jd_sections.get("requirements_preferred", None),
            )

            display_score_card(section.name, score)
            st.markdown("---")

        progress_bar.progress(idx / total)

    st.success("所有简历段落评分完成 ✅")
