# file: components/cards/analysis_card.py
import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from typing import Dict
from components.cards.base_card import BaseCard
from typing import Optional 


class AnalysisCard(BaseCard):
    def __init__(
        self,
        title: str = "Resume Analysis",
        icon: str = "📄",
        comment: Optional[str] = None,
        additional_content: Optional[str] = None,
    ):
        super().__init__(
            title=title,
            icon=icon,
            comment=comment,
            additional_content=additional_content
        )
        self.parser = ResumeParser()
        
    def render_section_content(self, section: str, content: str):
        st.subheader(section.upper())
        st.chat_message("Resumix").write(content)
    
    def render_analysis(self, text: str):
        sections = self.parser.parse_resume(text)
        for section, content in sections.items():
            self.render_section_content(section, content)
    
    def render(self):
        self.render_header()
        if self.comment:
            self.render_comment()
        self.render_additional()


def analysis_card(text: str):
    """Legacy function wrapper for backward compatibility"""
    logger.info("Handling Resume Analysis with provided resume text.")
    card = AnalysisCard()
    card.render()
    card.render_analysis(text)