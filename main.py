from paddleocr import PaddleOCR
import streamlit as st

from parser.resume_parser import ResumeParser
from utils.ocr_utils import OCRUtils
from utils.llm_client import LLMClient


from langchain.agents import initialize_agent, AgentType
from tool.tool import tool_list
from utils.llm_client import LLMWrapper, LLMClient
from parser.resume_rewriter import ResumeRewriter


llm_model = LLMClient(base_url="http://localhost:11434/api/generate", model_name="llama3.2:3b")
agent = initialize_agent(
    tools=tool_list,
    llm=LLMWrapper(client=llm_model),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

rewriter = ResumeRewriter(llm_model)
# Streamlit UI

st.set_page_config(
    page_title="RESUMIX",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📄RESUMIX - Resume Polisher")

uploaded_file = st.file_uploader("Upload PDF file", type="pdf")

jd_url = st.text_input("🧷输入岗位描述链接（可选）", placeholder="https://example.com/job-description")

task = "Polish"
tab1, tab2, tab3 = st.tabs(["简历解析", "推荐优化", "智能代理"])

if tab1:
    st.session_state.task = "Analyze"
elif tab2:
    st.session_state.task = "Polish"
elif tab3:
    st.session_state.task = "Agent"
    

if uploaded_file is not None:
    
    ocr_model = PaddleOCR(use_angle_cls=True, lang="ch")
    ocr = OCRUtils(ocr_model, dpi=150, keep_images=False)
    
    with st.spinner("Extracting text from PDF..."):
        text = ocr.extract_text(uploaded_file, max_pages=1)
        
        
    jd_content = ""
    if jd_url:
        from parser.jd_parser import JDParser
        jd_parser = JDParser(llm_model)
        jd_content = jd_parser.parse_from_url(jd_url)
        st.chat_message("Job Description").write(jd_content)
        
    
    if text:
        sections = {}
        with st.spinner("Extracting text from PDF..."):
            parser = ResumeParser()
        
            sections = parser.parse_resume(text)
        
        for section in sections:
            
            with st.spinner("Polishing section..."):
                
                result = ""
                
                if task == "Analyze":
                    result = rewriter.rewrite_section(section, jd_content)
                
                elif task == "Polish":
                    prompt = f"Please recommend improvements for the following resume section:\n\n{sections[section]}"
                    result = llm_model(prompt)
                elif task == "Agent":
                    prompt = f"""你是一个简历优化助手。请参考以下岗位描述，并优化简历内容：

                    岗位描述：{jd_content}

                    简历原文：
                    \"\"\"{section}\"\"\"

                    请按照如下格式作答：
                    Thought: ...
                    Action: local_llm_generate
                    Action Input: \"\"\"优化后的内容\"\"\"
                """
                    result = agent.run(prompt)
                    

            
                st.header(f"{section.upper()}")
            
                st.chat_message("Resumix").write(result)
    else:
        st.write("⚠️ No text found in the PDF.")
