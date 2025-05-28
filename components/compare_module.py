import streamlit as st
from streamlit_option_menu import option_menu
from parser.resume_parser import ResumeParser
from utils.logger import logger
from utils.i18n import LANGUAGES


def compare_resume_sections(text, jd_content, rewriter, method="llm"):
    logger.info("Comparing resume sections with method: {}".format(method))

    T = LANGUAGES[st.session_state.lang]
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    section_names = list(sections.keys())

    selected_section = option_menu(
        menu_title=None,
        options=section_names,
        icons=None,
        orientation="horizontal",  # 或 "horizontal"
    )

    original_text = sections[selected_section]
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"{T['compare']['original']}- {selected_section}")
        st.code(original_text)

    with col2:
        st.subheader(f"{T['compare']['polished']} - {selected_section}")
        with st.spinner("正在优化..."):
            if method == "llm":
                prompt = (
                    f"请优化以下简历段落，提高表达清晰度与专业性：\n\n{original_text}"
                )
                improved = rewriter.llm(prompt)
            elif method == "agent":
                improved = rewriter.rewrite_section(
                    selected_section, original_text, jd_content
                )
            else:
                improved = "⚠️ 未知优化方式"

        st.chat_message("Resumix").write(improved)
