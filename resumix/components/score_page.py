import streamlit as st
from utils.logger import logger
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from resumix.section.section_base import SectionBase
from resumix.modules.score_module.score_module import ScoreModule
from resumix.components.cards.score_card import ScoreCard
from resumix.components.base_page import BasePage
from resumix.utils.session_utils import SessionUtils


class ScorePage(BasePage):
    def __init__(self):
        super().__init__()

    def render(self):

        RESUME_SECTIONS = SessionUtils.get_resume_sections()
        JD_SECTIONS = SessionUtils.get_jd_sections()

        logger.info("开始简历评分分析（非顺序）...")

        score_module = ScoreModule()

        if "requirements_basic" not in JD_SECTIONS:
            st.warning(
                "❗岗位描述缺少关键字段（requirements_basic），无法进行评分分析。"
            )
            logger.warning(f"Missing Requirements Basic in JD Sections: {JD_SECTIONS}")
            return

        section_items = list(RESUME_SECTIONS.items())
        total = len(section_items)
        progress_bar = st.progress(0)

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_name = {
                executor.submit(
                    score_module.score_resume,
                    section,
                    JD_SECTIONS["requirements_basic"],
                    JD_SECTIONS.get("requirements_preferred"),
                ): name
                for name, section in section_items
            }

            finished = 0
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result = future.result()
                except Exception as e:
                    logger.warning(f"[Score] {name} 段落评分失败: {e}")
                    result = {"error": str(e)}

                # 立即展示（可能无序）
                section = RESUME_SECTIONS[name]
                with st.spinner(f"正在展示 {section.name}..."):
                    score_card = ScoreCard(section.name, result)
                    score_card.render()
                    st.markdown("---")

                finished += 1
                progress_bar.progress(finished / total)

        st.success("所有简历段落评分完成 ✅")
