# file: components/cards/compare_card.py
from streamlit_option_menu import option_menu
import streamlit as st
from loguru import logger
from typing import Dict
from section.section_base import SectionBase
from utils.i18n import LANGUAGES
from resumix.rewriter.resume_rewriter import ResumeRewriter
from components.cards.section_render import SectionRender
from components.cards.base_card import BaseCard
from typing import Optional 


class CompareCard(BaseCard):
    def __init__(
        self,
        title: str = "Resume Comparison",
        icon: str = "🔄",
        comment: Optional[str] = None,
        additional_content: Optional[str] = None,
    ):
        super().__init__(
            title=title,
            icon=icon,
            comment=comment,
            additional_content=additional_content
        )
        self.T = LANGUAGES[st.session_state.lang]
        
    def render_original_section(self, section_name: str, section_obj: SectionBase):
        """Render the original content column"""
        st.markdown(f"#### {self.T['compare']['original']} - {section_name}")
        st.chat_message("user").write("以下是简历中的内容：")
        with st.chat_message("user"):
            for line in section_obj.original_lines:
                st.markdown(
                    line if line.strip() else "&nbsp;", unsafe_allow_html=True
                )
    
    def render_polished_section(self, section_name: str, section_obj: SectionBase):
        """Render the polished content column"""
        st.markdown(f"#### {self.T['compare']['polished']} - {section_name}")
        st.chat_message("assistant").write("这是润色后的内容：")
        try:
            SectionRender().render_section(section_obj)
        except Exception as e:
            st.error(f"❌ 渲染出错：{e}")
    
    def render_section_comparison(self, section_name: str, section_obj: SectionBase):
        """Render comparison for a single section"""
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            self.render_original_section(section_name, section_obj)
        with col2:
            self.render_polished_section(section_name, section_obj)
    
    def render_comparison(
        self,
        sections: Dict[str, SectionBase],
        jd_content: str,
        rewriter: ResumeRewriter,
    ):
        """Main comparison rendering logic"""
        logger.info("Comparing all resume sections using SectionRewriter")
        
        for section_name, section_obj in sections.items():
            # Rewrite section if not already rewritten
            if not getattr(section_obj, "rewritten_text", None):
                with st.spinner(f"正在润色 [{section_name}] 模块..."):
                    rewriter.rewrite_section(section_obj, jd_content)
            
            self.render_section_comparison(section_name, section_obj)
    
    def render(self):
        self.render_header()
        if self.comment:
            self.render_comment()
        self.render_additional()


def compare_resume_sections(
    sections: Dict[str, SectionBase],
    jd_content: str,
    rewriter: ResumeRewriter,
):
    """Legacy function wrapper for backward compatibility"""
    logger.info("Comparing all resume sections using SectionRewriter")
    card = CompareCard()
    card.render()
    card.render_comparison(sections, jd_content, rewriter)