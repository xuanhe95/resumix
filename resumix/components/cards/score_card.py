# components/cards/score_card.py
import streamlit as st
from typing import Dict
from components.cards.display_card import display_card  # Updated import
from job_parser.resume_parser import ResumeParser
from utils.logger import logger

def display_score_card(section_name: str, scores: dict):
    """Display resume section score card"""
    display_card(
        title=f"{section_name} 评分",
        icon="📊",
        scores={
            "完整性": scores.get("完整性", 0),
            "清晰度": scores.get("清晰度", 0),
            "匹配度": scores.get("匹配度", 0),
            "表达专业性": scores.get("表达专业性", 0),
            "成就导向": scores.get("成就导向", 0),
            "数据支撑": scores.get("数据支撑", 0)
        },
        comment=scores.get("评语", "无")
    )

def analyze_resume_with_scores(sections: Dict[str, dict], jd_content: str, llm_model, use_card_template: bool = False):
    """Analyze resume with scoring system"""
    logger.info("Analyzing resume with scoring system")
    
    # Example scoring logic - replace with your actual implementation
    sample_scores = {
        "完整性": 8,
        "清晰度": 7,
        "匹配度": 6 if jd_content else 5,
        "表达专业性": 8,
        "成就导向": 7,
        "数据支撑": 5,
        "评语": "简历整体良好，但可增加更多量化成果"
    }
    
    if use_card_template:
        for section_name, section_content in sections.items():
            display_score_card(section_name, sample_scores)
    else:
        # Original non-card display
        st.header("📊 简历评分分析")
        for section_name, section_content in sections.items():
            st.subheader(section_name)
            st.json(sample_scores)
            st.markdown(f"**评语:** {sample_scores['评语']}")
            st.divider()