import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger


def agent_card(text):
    logger.info("Handling Resume Agent with provided resume text.")
    st.header("🤖 AI Agent")


def handle_agent(text, jd_content, agent):
    logger.info(
        "Handling AI Agent with provided resume text and job description content."
    )
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
