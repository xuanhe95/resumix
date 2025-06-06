## from paddleocr import PaddleOCR
import streamlit as st

from pathlib import Path

from parser.jd_parser import JDParser
from utils.ocr_utils import OCRUtils
from utils.llm_client import LLMClient


from langchain.agents import initialize_agent, AgentType
from tool.tool import tool_list
from utils.llm_client import LLMWrapper, LLMClient
from parser.resume_rewriter import ResumeRewriter

from config import Config

from streamlit_option_menu import option_menu
from streamlit_card import card

from components.analysis_module import analysis_card
from components.polish_module import polish_card
from components.agent_module import agent_card
from components.score_module import analyze_resume_with_scores
from components.compare_module import compare_resume_sections

from utils.session_utils import SessionUtils

from utils.i18n import LANGUAGES

CONFIG = Config().config

CURRENT_DIR = Path(__file__).resolve().parent
ASSET_DIR = CURRENT_DIR / "assets" / "logo.png"


st.set_page_config(
    page_title="RESUMIX",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "lang" not in st.session_state:
    st.session_state.lang = "en"


T = LANGUAGES[st.session_state.lang]

# card(
#     title=T["title"],
#     text="test",
#     image="assets/logo.png",
#     url="www.resumix.com",
# )


llm_model = LLMClient(base_url=CONFIG.LLM.URL, model_name=CONFIG.LLM.MODEL)
agent = initialize_agent(
    tools=tool_list,
    llm=LLMWrapper(client=llm_model),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)

rewriter = ResumeRewriter(llm_model)


col1, col2 = st.columns([1, 3])
with col1:
    st.image(ASSET_DIR, width=60)
    pass
with col2:
    st.title(T["title"])

# ========== 页面主入口 ==========
tab_names = T["tabs"]

tab = option_menu(
    menu_title=None,
    options=tab_names,
    icons=[
        "file-text",
        "pencil",
        "robot",
        "bar-chart",
        "file-earmark-break",
    ],
    orientation="horizontal",
)


uploaded_file = None
with st.sidebar:

    with st.expander(T["upload_resume"], expanded=True):
        uploaded_file = st.file_uploader(T["upload_resume_title"], type=["pdf"])
        SessionUtils.upload_resume_file(uploaded_file)

    with st.expander(T["job_description"], expanded=True):
        jd_url = st.text_input(
            T["job_description_title"],
            placeholder="https://example.com/job-description",
        )

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

    with st.expander(T["language"], expanded=False):
        selected_lang = st.selectbox(
            "Global",
            ["en", "zh"],
            index=["en", "zh"].index(st.session_state.lang),
        )
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()  # 切换语言后刷新页面

if uploaded_file:

    if "resume_text" not in st.session_state:
        st.session_state.resume_text = SessionUtils.get_resume_text()
    text = st.session_state.resume_text

    if tab == tab_names[0]:
        analysis_card(text)
    elif tab == tab_names[1]:
        polish_card(text, llm_model)
    elif tab == tab_names[2]:
        agent_card(text)
    elif tab == tab_names[3]:
        jd_content = SessionUtils.get_job_description_content()
        analyze_resume_with_scores(text, jd_content, llm_model)
    elif tab == tab_names[4]:
        jd_content = SessionUtils.get_job_description_content()
        compare_resume_sections(text, jd_content, rewriter, method="llm")
else:
    st.info(T["please_upload"])
