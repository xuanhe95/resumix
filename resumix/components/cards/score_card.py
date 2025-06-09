import streamlit as st
from loguru import logger
import matplotlib.pyplot as plt


def display_score_card(section_name: str, scores: dict):
    """
    展示单个简历段落评分的卡片组件：雷达图 + 维度得分表 + 评语。
    支持中文显示，并包含 6 项评分维度。
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib

    logger.info(f"Displaying scores for section: {section_name} - {scores}")
    st.markdown(f"### 📊 {section_name} 评分")

    # 设置中文字体（适配 matplotlib）
    matplotlib.rcParams["font.family"] = "PingFang SC"

    matplotlib.rcParams["axes.unicode_minus"] = False

    # 准备数据（扩展为 6 项）
    df = pd.DataFrame(
        {
            "维度": [
                "完整性",
                "清晰度",
                "匹配度",
                "表达专业性",
                "成就导向",
                "数据支撑",
            ],
            "得分": [
                scores.get("完整性", 0),
                scores.get("清晰度", 0),
                scores.get("匹配度", 0),
                scores.get("表达专业性", 0),
                scores.get("成就导向", 0),
                scores.get("数据支撑", 0),
            ],
        }
    )

    # 雷达图数据准备
    labels = df["维度"].tolist()
    values = df["得分"].tolist()
    values += values[:1]  # 闭合雷达图
    angles = [n / float(len(labels)) * 2 * 3.1415926 for n in range(len(labels))]
    angles += angles[:1]

    # 展示组件
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
        st.markdown(f"📝 **评语：** {scores.get('评语', '无')}")
