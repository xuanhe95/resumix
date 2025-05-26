from paddleocr import PaddleOCR
import streamlit as st

from parser.resume_parser import ResumeParser
from parser.jd_parser import JDParser
from utils.ocr_utils import OCRUtils
from utils.llm_client import LLMClient


from langchain.agents import initialize_agent, AgentType
from tool.tool import tool_list
from utils.llm_client import LLMWrapper, LLMClient
from parser.resume_rewriter import ResumeRewriter

from config import Config
from loguru import logger


CONFIG = Config().config

llm_model = LLMClient(base_url=CONFIG.LLM.URL, model_name=CONFIG.LLM.MODEL)
ocr_model = PaddleOCR(use_angle_cls=True, lang="ch")
ocr = OCRUtils(ocr_model, dpi=150, keep_images=False)
agent = initialize_agent(
    tools=tool_list,
    llm=LLMWrapper(client=llm_model),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)

rewriter = ResumeRewriter(llm_model)
# Streamlit UI

st.set_page_config(
    page_title="RESUMIX",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("RESUMIX")


# ========== 公共函数 ==========
@st.cache_data
def extract_text_from_pdf(file):
    return ocr.extract_text(file, max_pages=1)


def display_job_description(jd_url, llm_model):
    jd_parser = JDParser(llm_model)
    jd_content = jd_parser.parse_from_url(jd_url)
    st.chat_message("Job Description").write(jd_content)
    return jd_content


# ========== 各 Tab 功能模块 ==========
def handle_analyze(text):
    st.header("📄 Resume Analysis")
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    for section, content in sections.items():
        st.subheader(section.upper())
        st.chat_message("Resumix").write(content)


def handle_polish(text, llm_model):
    st.header("✨ Resume Polishing")
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    for section, content in sections.items():
        prompt = f"Please recommend improvements for the following resume section:\n\n{content}"
        result = llm_model(prompt)
        st.chat_message("Resumix").write(result)


def handle_agent(text, jd_content, agent):
    st.header("🤖 AI Agent")
    parser = ResumeParser()
    sections = parser.parse_resume(text)
    for section, content in sections.items():
        prompt = f"""你是一个简历优化助手。请参考以下岗位描述，并优化简历内容：

            岗位描述：{jd_content}

            简历原文：
\"\"\"{content}\"\"\"

请按照如下格式作答：
Thought: ...
Action: local_llm_generate
Action Input: \"\"\"优化后的内容\"\"\"
"""
        result = agent.run(prompt)
        st.chat_message("Resumix").write(result)


# ========== 页面主入口 ==========
tab1, tab2, tab3 = st.tabs(["简历解析", "推荐优化", "智能代理"])
with st.sidebar:
    with st.expander("📎 Upload Resume", expanded=True):
        uploaded_file = st.file_uploader("Upload Resume", type=["pdf"])

    with st.expander("💼 Job Description", expanded=True):
        jd_url = st.text_input(
            "JD Link (URL)", placeholder="https://example.com/job-description"
        )

    with st.expander("🔐 User Login"):
        if not st.session_state.get("authenticated"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if username == "admin" and password == "123456":
                    st.session_state.authenticated = True
                    st.success("Login Success")
        else:
            st.success("Logged in")
            if st.button("Logout"):
                st.session_state.authenticated = False


if uploaded_file:
    text = extract_text_from_pdf(uploaded_file)

    with tab1:
        handle_analyze(text)

    with tab2:
        handle_polish(text, llm_model)

    with tab3:
        if jd_url:
            jd_content = display_job_description(jd_url, llm_model)
            handle_agent(text, jd_content, agent)
        else:
            st.warning(
                "Please provide a job description URL to use the AI Agent feature."
            )
else:
    st.info("Please upload a resume PDF file to get started.")
