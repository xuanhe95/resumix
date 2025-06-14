import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger


def analysis_card(text):
    logger.info("Handling Resume Analysis with provided resume text.")
    st.header("📄 Resume Analysis")
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    for section, content in sections.items():
        st.subheader(section.upper())
        st.chat_message("Resumix").write(content)
