import streamlit as st
from parser.resume_parser import ResumeParser
from utils.logger import logger


def polish_card(text, llm_model):
    logger.info("Handling Resume Polishing with provided resume text.")
    st.header("✨ Resume Polishing")
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    for section, content in sections.items():
        prompt = f"Please recommend improvements for the following resume section:\n\n{content}"
        result = llm_model(prompt)
        st.chat_message("Resumix").write(result)
