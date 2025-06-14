from typing import Dict, Optional
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from loguru import logger

def display_card(
    title: str,
    icon: str,
    scores: Dict[str, float],
    comment: Optional[str] = None,
    additional_content: Optional[str] = None,
    dimensions: Optional[list] = None
):
    """
    Universal card template for both Score and Agent cards.
    
    Args:
        title: Card title (e.g., "简历评分")
        icon: Emoji icon (e.g., "📊")
        scores: Dictionary of scores for each dimension
        comment: Optional comment text
        additional_content: Optional extra content to display below
        dimensions: Custom dimension names (default uses standard 6 dimensions)
    """
    # Set Chinese font
    matplotlib.rcParams["font.family"] = "PingFang SC"
    matplotlib.rcParams["axes.unicode_minus"] = False

    logger.info(f"Displaying card: {title}")

    # Default dimensions
    default_dims = [
        "完整性", "清晰度", "匹配度", 
        "表达专业性", "成就导向", "数据支撑"
    ]
    dims = dimensions or default_dims
    
    # Prepare data
    df = pd.DataFrame({
        "维度": dims,
        "得分": [scores.get(dim, 0) for dim in dims]
    })

    # Radar chart
    labels = df["维度"].tolist()
    values = df["得分"].tolist()
    values += values[:1]  # Close radar
    angles = [n / float(len(labels)) * 2 * 3.1415926 for n in range(len(labels))]
    angles += angles[:1]

    # Display
    st.markdown(f"### {icon} {title}")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        fig, ax = plt.subplots(figsize=(3.5, 3.5), subplot_kw=dict(polar=True))
        ax.plot(angles, values, linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids([a * 180 / 3.1415926 for a in angles[:-1]], labels)
        ax.set_ylim(0, 10)
        st.pyplot(fig, clear_figure=True)

    with col2:
        st.dataframe(df.set_index("维度"), use_container_width=True, height=180)
        if comment:
            st.markdown(f"📝 **评语：** {comment}")
    
    if additional_content:
        st.markdown("---")
        st.markdown(additional_content)