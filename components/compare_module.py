from streamlit_option_menu import option_menu
import streamlit as st
from loguru import logger
from typing import Dict
from section.section_base import SectionBase
from utils.i18n import LANGUAGES
from parser.resume_rewriter import ResumeRewriter  # 你自己的实现路径
from components.cards.section_render import SectionRender  # 你自己的实现路径


def compare_resume_sections(
    sections: Dict[str, SectionBase],
    jd_content: str,
    rewriter: ResumeRewriter,
):
    logger.info("Comparing all resume sections using SectionRewriter")

    T = LANGUAGES[st.session_state.lang]

    for section_name, section_obj in sections.items():
        st.divider()  # 分隔每个模块

        # 若未润色过，调用 Rewriter 润色
        if not getattr(section_obj, "rewritten_text", None):
            with st.spinner(f"正在润色 [{section_name}] 模块..."):
                rewriter.rewrite_section(section_obj, jd_content)

        col1, col2 = st.columns(2)

        # 原始内容列
        with col1:
            st.markdown(f"#### {T['compare']['original']} - {section_name}")
            st.chat_message("user").write("以下是简历中的内容：")
            with st.chat_message("user"):
                for line in section_obj.original_lines:
                    st.markdown(
                        line if line.strip() else "&nbsp;", unsafe_allow_html=True
                    )

        # 润色内容列
        with col2:
            st.markdown(f"#### {T['compare']['polished']} - {section_name}")
            st.chat_message("assistant").write("这是润色后的内容：")

            try:
                SectionRender().render_section(section_obj)
            except Exception as e:
                st.error(f"❌ 渲染出错：{e}")
