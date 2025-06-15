# components/cards/score_card.py
import streamlit as st
from resumix.utils.logger import logger
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

from typing import Dict
from resumix.components.cards.display_card import display_card  # Updated import
from resumix.job_parser.resume_parser import ResumeParser
from resumix.utils.logger import logger


def display_score_card(section_name: str, scores: dict):
    """
    Display a score card for a resume section, including a radar chart,
    a score table, and a comment. Supports any number of scoring dimensions
    based on the input JSON (Python dict).
    """
    logger.info(f"Displaying scores for section: {section_name} - {scores}")
    st.markdown(f"### 📊 Score for {section_name}")

    # 设置中文字体（适配 matplotlib）
    matplotlib.rcParams["font.family"] = "Arial"
    matplotlib.rcParams["axes.unicode_minus"] = False

    # Filter numeric score dimensions only
    score_items = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
    comment = scores.get("Comment") or scores.get("评语") or "No comment provided."

    # Create score DataFrame
    df = pd.DataFrame(
        {
            "Dimension": list(score_items.keys()),
            "Score": list(score_items.values()),
        }
    )

    # Radar chart data preparation
    labels = df["Dimension"].tolist()
    values = df["Score"].tolist()
    values += values[:1]  # Close the radar chart loop
    angles = [n / float(len(labels)) * 2 * 3.1415926 for n in range(len(labels))]
    angles += angles[:1]

    # Layout: radar chart and table
    col1, col2 = st.columns([1, 2])

    with col1:
        fig, ax = plt.subplots(figsize=(3.5, 3.5), subplot_kw=dict(polar=True))
        ax.plot(angles, values, linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids([a * 180 / 3.1415926 for a in angles[:-1]], labels)
        ax.set_ylim(0, 10)
        st.pyplot(fig, clear_figure=True)

    with col2:
        st.dataframe(df.set_index("Dimension"), use_container_width=True, height=180)
        st.markdown(f"📝 **Comment:** {comment}")


def analyze_resume_with_scores(
    sections: Dict[str, dict],
    jd_content: str,
    llm_model,
    use_card_template: bool = False,
):
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
        "评语": "简历整体良好，但可增加更多量化成果",
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
