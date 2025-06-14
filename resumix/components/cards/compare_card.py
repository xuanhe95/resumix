from streamlit_option_menu import option_menu
import streamlit as st
from loguru import logger
from typing import Dict
from section.section_base import SectionBase
from utils.i18n import LANGUAGES
from job_parser.resume_rewriter import ResumeRewriter
from components.cards.section_render import SectionRender
from .display_card import display_card  # Import the shared template

def compare_resume_sections(
    sections: Dict[str, SectionBase],
    jd_content: str,
    rewriter: ResumeRewriter,
    use_card_template: bool = False
):
    """
    Compare resume sections with optional card template display
    
    Args:
        sections: Dictionary of resume sections
        jd_content: Job description content
        rewriter: Resume rewriter instance
        use_card_template: Whether to use the card template (default False)
    """
    logger.info("Comparing all resume sections using SectionRewriter")
    T = LANGUAGES[st.session_state.lang]

    for section_name, section_obj in sections.items():
        st.divider()

        # Rewrite section if not already rewritten
        if not getattr(section_obj, "rewritten_text", None):
            with st.spinner(f"正在润色 [{section_name}] 模块..."):
                rewriter.rewrite_section(section_obj, jd_content)

        if use_card_template:
            # Card template version
            _display_comparison_card(section_name, section_obj, T)
        else:
            # Original two-column version
            _display_comparison_columns(section_name, section_obj, T)

def _display_comparison_card(section_name: str, section_obj: SectionBase, T: dict):
    """Display comparison using the card template"""
    display_card(
        title=f"{section_name} 对比",
        icon="🔍",
        scores={
            "相似度": _calculate_similarity(section_obj),
            "专业性": _calculate_professionalism(section_obj),
            "匹配度": _calculate_relevance(section_obj),
            "完成度": _calculate_completeness(section_obj),
            "数据支撑": _calculate_data_support(section_obj)
        },
        comment="左右滑动查看原始与润色版本对比",
        additional_content=_generate_comparison_content(section_name, section_obj, T),
        dimensions=["相似度", "专业性", "匹配度", "完成度", "数据支撑"]
    )

def _display_comparison_columns(section_name: str, section_obj: SectionBase, T: dict):
    """Original two-column display version"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### {T['compare']['original']} - {section_name}")
        st.chat_message("user").write("以下是简历中的内容：")
        with st.chat_message("user"):
            for line in section_obj.original_lines:
                st.markdown(line if line.strip() else "&nbsp;", unsafe_allow_html=True)

    with col2:
        st.markdown(f"#### {T['compare']['polished']} - {section_name}")
        st.chat_message("assistant").write("这是润色后的内容：")
        try:
            SectionRender().render_section(section_obj)
        except Exception as e:
            st.error(f"❌ 渲染出错：{e}")

def _generate_comparison_content(section_name: str, section_obj: SectionBase, T: dict) -> str:
    """Generate expandable comparison content for card template"""
    with st.expander(f"查看 {section_name} 详细对比"):
        _display_comparison_columns(section_name, section_obj, T)
    return ""

# Scoring calculation methods (implement according to your needs)
def _calculate_similarity(section_obj: SectionBase) -> float:
    """Calculate similarity between original and rewritten content"""
    return 7.0  # Implement your actual calculation

def _calculate_professionalism(section_obj: SectionBase) -> float:
    """Calculate professionalism score"""
    return 8.0  # Implement your actual calculation

def _calculate_relevance(section_obj: SectionBase) -> float:
    """Calculate relevance to job description"""
    return 6.5  # Implement your actual calculation

def _calculate_completeness(section_obj: SectionBase) -> float:
    """Calculate completeness score"""
    return 9.0  # Implement your actual calculation

def _calculate_data_support(section_obj: SectionBase) -> float:
    """Calculate data/achievement support score"""
    return 5.5  # Implement your actual calculation