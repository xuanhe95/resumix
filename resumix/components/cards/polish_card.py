import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from .display_card import display_card  # Import your shared template


def polish_card(text: str, llm_model, show_scores: bool = False):
    """
    Enhanced polish card using the shared template

    Args:
        text: Resume text to polish
        llm_model: LLM model for generating improvements
        show_scores: Whether to display scoring visualization
    """
    logger.info("Handling Resume Polishing with provided resume text.")
    parser = ResumeParser()
    sections = parser.parse_resume(text)

    if show_scores:
        # Card template version with scores
        display_card(
            title="简历润色",
            icon="✨",
            scores={
                "语言流畅度": 8,
                "专业性": 7,
                "清晰度": 6,
                "结构合理性": 7,
                "成就突出度": 5,
            },
            comment="AI建议的改进方案如下",
            additional_content=_generate_polish_content(sections, llm_model),
            dimensions=["语言流畅度", "专业性", "清晰度", "结构合理性", "成就突出度"],
        )
    else:
        # Original simple version
        st.markdown("### ✨ 简历润色")
        _generate_polish_content(sections, llm_model)


def _generate_polish_content(sections: dict, llm_model):
    """Generate the polish suggestions content"""
    with st.expander("查看AI润色建议", expanded=True):
        for section, content in sections.items():
            if not content.strip():
                continue

            prompt = f"""请为以下简历段落提供改进建议，重点关注：
1. 语言表达的流畅性和专业性
2. 成就和技能的突出展示
3. 与行业标准的符合程度

需要润色的内容：
\"\"\"{content}\"\"\"

请按以下格式提供建议：
- 主要问题分析
- 具体改进建议
- 优化后的示例内容
"""
            result = llm_model(prompt)
            st.chat_message("Resumix").write(result)
            st.markdown("---")
