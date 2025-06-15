# file: components/cards/polish_card.py
import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from typing import Callable, Dict
from components.cards.base_card import BaseCard
from typing import Optional 


class PolishCard(BaseCard):
    def __init__(
        self,
        title: str = "Resume Polishing",
        icon: str = "✨",
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
        
    def render_polish_result(self, result: str):
        """Render the polished result from LLM"""
        st.chat_message("Resumix").write(result)
    
    def render_section_polish(self, section: str, content: str, llm_model: Callable):
        """Render polishing for a single section"""
        prompt = f"Please recommend improvements for the following resume section:\n\n{content}"
        result = llm_model(prompt)
        self.render_polish_result(result)
    
    def render_polishing(
        self,
        text: str,
        llm_model: Callable
    ):
        """Main polishing rendering logic"""
        logger.info("Polishing all resume sections using LLM")
        sections = self.parser.parse_resume(text)
        
        for section, content in sections.items():
            st.subheader(section)
            self.render_section_polish(section, content, llm_model)
            st.divider()
    
    def render(self):
        self.render_header()
        if self.comment:
            self.render_comment()
        self.render_additional()


def polish_card(text: str, llm_model: Callable):
    """Legacy function wrapper for backward compatibility"""
    logger.info("Handling Resume Polishing with provided resume text.")
    card = PolishCard()
    card.render()
    card.render_polishing(text, llm_model)