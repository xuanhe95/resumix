# analysis_card.py
import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from resumix.components.cards.display_card import display_card


def analysis_card(text: str, show_analysis: bool = True, show_scores: bool = False):
    """
    Display resume analysis card using the shared template.

    Args:
        text: Resume text to analyze
        show_analysis: Whether to show parsed sections (default True)
        show_scores: Whether to display scores radar chart (default False)
    """
    logger.info("Handling Resume Analysis with provided resume text.")
    parser = ResumeParser()
    sections = parser.parse_resume(text)

    if show_scores:
        # Display with full score card template
        display_card(
            title="简历分析",
            icon="📄",
            scores={
                "完整性": calculate_completeness(sections),
                "清晰度": calculate_clarity(sections),
                "匹配度": 5,  # Placeholder - implement your own logic
                "表达专业性": 7,
                "成就导向": 6,
                "数据支撑": 4,
            },
            comment="简历解析完成，点击下方查看详细内容",
            additional_content=(
                generate_section_content(sections) if show_analysis else None
            ),
        )
    else:
        # Simple view (original functionality)
        st.markdown("### 📄 简历分析")
        if show_analysis:
            generate_section_content(sections)


def generate_section_content(sections: dict):
    """Generate the expandable section content"""
    with st.expander("查看详细解析", expanded=True):
        for section, content in sections.items():
            st.subheader(section.upper())
            st.chat_message("Resumix").write(content)


def calculate_completeness(sections: dict) -> int:
    """Calculate completeness score (example implementation)"""
    required_sections = {"工作经历", "教育背景", "技能"}
    present_sections = set(sections.keys())
    return min(10, len(present_sections & required_sections) * 3)


def calculate_clarity(sections: dict) -> int:
    """Calculate clarity score (robust version)"""
    total_length = sum(len(str(content)) for content in sections.values() if content)
    return min(10, max(3, 10 - total_length // 500))
