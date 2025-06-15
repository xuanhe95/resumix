import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from .display_card import display_card  # Import the shared template


def agent_card(text: str, jd_content: str = None, agent=None):
    """Display AI agent card using the universal template"""
    # Agent-specific scores
    agent_scores = {
        "响应速度": 8,
        "建议质量": 9,
        "匹配优化": 7 if jd_content else 5,
        "语言流畅度": 8,
        "实用性": 7,
        "创新性": 6,
    }

    # Generate optimization content if agent provided
    additional_content = None
    if text and agent:
        additional_content = generate_optimization_content(text, jd_content, agent)

    display_card(
        title="AI 优化助手",
        icon="🤖",
        scores=agent_scores,
        comment="AI助手可以提供简历优化建议，匹配岗位要求后效果更佳。",
        additional_content=additional_content,
        dimensions=list(agent_scores.keys()),  # Use custom dimensions
    )


def generate_optimization_content(text, jd_content, agent):
    """Generate the optimization suggestions content"""
    content = []
    parser = ResumeParser()
    sections = parser.parse_resume(text)

    with st.expander("🔍 查看详细优化建议"):
        for section, section_text in sections.items():
            if not section_text.strip():
                continue

            st.markdown(f"#### {section}优化建议")
            prompt = f"""你是一个简历优化助手。请参考以下岗位描述，并优化简历内容：
                岗位描述：{jd_content or '无特定岗位要求'}
                简历原文：\"\"\"{section_text}\"\"\"
            """
            result = agent.run(prompt)
            st.chat_message("Resumix").write(result)

    return "\n".join(content)
