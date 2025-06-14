#from paddleocr import PaddleOCR
import streamlit as st
import sys
import os
from pathlib import Path
from langchain.agents import initialize_agent, AgentType
from config import Config
from streamlit_option_menu import option_menu

# Import card components
from components.cards.analysis_card import analysis_card
from components.cards.polish_card import polish_card
from components.cards.agent_card import agent_card
from components.cards.score_card import (
    display_score_card,
    analyze_resume_with_scores
)
from components.cards.compare_card import compare_resume_sections

# Import utilities
from utils.ocr_utils import OCRUtils
from utils.llm_client import LLMClient, LLMWrapper
from utils.session_utils import SessionUtils
from utils.i18n import LANGUAGES
from job_parser.resume_rewriter import ResumeRewriter
from job_parser.jd_parser import JDParser
from tool.tool import tool_list

# Config setup
CONFIG = Config().config
CURRENT_DIR = Path(__file__).resolve().parent
ASSET_DIR = CURRENT_DIR / "assets" / "logo.png"

# Initialize session state
if "lang" not in st.session_state:
    st.session_state.lang = "en"

T = LANGUAGES[st.session_state.lang]

# Initialize LLM and agent
llm_model = LLMClient(base_url=CONFIG.LLM.URL, model_name=CONFIG.LLM.MODEL)
agent = initialize_agent(
    tools=tool_list,
    llm=LLMWrapper(client=llm_model),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)

RESUME_REWRITER = ResumeRewriter(llm_model)

# Page configuration
st.set_page_config(
    page_title="RESUMIX",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Header section
header_col1, header_col2 = st.columns([1, 3])
with header_col1:
    st.image(ASSET_DIR, width=60)
with header_col2:
    st.title(T["title"])

# Main navigation
tab_names = T["tabs"]
selected_tab = option_menu(
    menu_title=None,
    options=tab_names,
    icons=["file-text", "pencil", "robot", "bar-chart", "file-earmark-break"],
    orientation="horizontal",
)

# Sidebar components
with st.sidebar:
    # Resume upload
    with st.expander(T["upload_resume"], expanded=True):
        uploaded_file = st.file_uploader(T["upload_resume_title"], type=["pdf"])
        SessionUtils.upload_resume_file(uploaded_file)

    # Job description
    with st.expander(T["job_description"], expanded=True):
        jd_url = st.text_input(
            T["job_description_title"],
            placeholder="https://example.com/job-description",
        )

    # Authentication
    with st.expander(T["user_login"], expanded=False):
        if not st.session_state.get("authenticated"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button(T["login_button"]):
                if username == "admin" and password == "123456":
                    st.session_state.authenticated = True
                    st.success(T["login_success"])
        else:
            st.success(T["logged_in"])
            if st.button(T["logout"]):
                st.session_state.authenticated = False

    # Language selection
    with st.expander(T["language"], expanded=False):
        selected_lang = st.selectbox(
            "Global",
            ["en", "zh"],
            index=["en", "zh"].index(st.session_state.lang),
        )
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

# Main content area
if uploaded_file:
    # Initialize session data if not exists
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = SessionUtils.get_resume_text()
    
    text = st.session_state.resume_text
    STRUCTED_SECTIONS = SessionUtils.get_resume_sections()
    jd_content = SessionUtils.get_job_description_content()

    # Tab routing with card components
    with st.container():
        if selected_tab == tab_names[0]:  # Analysis
            analysis_card(
                text=text,
                show_scores=True,
                show_analysis=True
            )
            
        elif selected_tab == tab_names[1]:  # Polish
            polish_card(
                text=text,
                llm_model=llm_model,
                show_scores=False
            )
            
        elif selected_tab == tab_names[2]:  # Agent
            agent_card(
                text=text,
                jd_content=jd_content,
                agent=agent,
                show_scores=True
            )
            
        elif selected_tab == tab_names[3]:  # Score
            analyze_resume_with_scores(
                sections=STRUCTED_SECTIONS,
                jd_content=jd_content,
                llm_model=llm_model,
                use_card_template=True
            )
            
        elif selected_tab == tab_names[4]:  # Compare
            compare_resume_sections(
                sections=STRUCTED_SECTIONS,
                jd_content=jd_content,
                rewriter=RESUME_REWRITER,
                use_card_template=True
            )
else:
    st.info(T["please_upload"])