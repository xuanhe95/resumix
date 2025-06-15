import streamlit as st
from resumix.utils.logger import logger
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib


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
