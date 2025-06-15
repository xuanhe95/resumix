# from paddleocr import PaddleOCR
import streamlit as st
import concurrent.futures
from pathlib import Path

# Initialize session state
if "lang" not in st.session_state:
    st.session_state.lang = "en"

# Import card components (updated imports)
from resumix.components.cards.analysis_card import AnalysisCard
from resumix.components.cards.polish_card import PolishCard
from resumix.components.cards.agent_card import AgentCard
from resumix.components.cards.score_card import ScoreCard
from resumix.components.cards.compare_card import CompareCard

# Import utilities and other components
from utils.ocr_utils import OCRUtils
from utils.llm_client import LLMClient, LLMWrapper
from utils.session_utils import SessionUtils
from utils.i18n import LANGUAGES
from job_parser.resume_rewriter import ResumeRewriter
from job_parser.jd_parser import JDParser
from tool.tool import tool_list
from resumix.utils.logger import logger
from resumix.components.score_page import ScorePage
from config.config import Config
from langchain.agents import initialize_agent, AgentType

# Config setup
CONFIG = Config().config
CURRENT_DIR = Path(__file__).resolve().parent
ASSET_DIR = CURRENT_DIR / "assets" / "logo.png"

T = LANGUAGES[st.session_state.lang]

# Initialize LLM and agent
llm_model = LLMClient()
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
            key="jd_url",
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

def prefetch_resume_sections():
    try:
        st.session_state.resume_sections = SessionUtils.get_resume_sections()
        logger.info("[后台] Resume section 提取完成")
    except Exception as e:
        logger.warning(f"[后台] 提取 resume_sections 失败: {e}")

def prefetch_jd_sections():
    try:
        st.session_state.jd_sections = SessionUtils.get_jd_sections()
        logger.info("[后台] JD section 提取完成")
    except Exception as e:
        logger.warning(f"[后台] 提取 jd_sections 失败: {e}")

if uploaded_file:
    # Initialize session data if not exists
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = SessionUtils.get_resume_text()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    # Background section extraction (non-blocking)
    if "resume_sections" not in st.session_state:
        executor.submit(prefetch_resume_sections)

    text = st.session_state.resume_text
    STRUCTED_SECTIONS = SessionUtils.get_resume_sections()
    jd_content = SessionUtils.get_job_description_content()

    # Sample scores data (replace with your actual scoring logic)
    sample_scores = {
        "完整性": 8,
        "清晰度": 7,
        "匹配度": 6 if jd_content else 5,
        "表达专业性": 8,
        "成就导向": 7,
        "数据支撑": 5,
        "评语": "简历整体良好，但可增加更多量化成果",
    }

    # Tab routing with updated card components
    with st.container():
        if selected_tab == tab_names[0]:  # Analysis
            analysis_card = AnalysisCard()
            analysis_card.render()
            analysis_card.render_analysis(text)

        elif selected_tab == tab_names[1]:  # Polish
            polish_card = PolishCard()
            polish_card.render()
            polish_card.render_polishing(text, llm_model)

        elif selected_tab == tab_names[2]:  # Agent
            agent_card = AgentCard()
            agent_card.render()
            agent_card.render_agent_interaction(text, jd_content, agent)

        elif selected_tab == tab_names[3]:  # Score
            ScorePage().render()
            # Alternatively, using ScoreCard for each section:
            # for section_name in STRUCTED_SECTIONS.keys():
            #     score_card = ScoreCard(section_name, sample_scores)
            #     score_card.render()

        elif selected_tab == tab_names[4]:  # Compare
            compare_card = CompareCard()
            compare_card.render()
            compare_card.render_comparison(STRUCTED_SECTIONS, jd_content, RESUME_REWRITER)
else:
    st.info(T["please_upload"])