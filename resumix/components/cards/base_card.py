# file: components/cards/base_card.py

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from typing import Dict, Optional, List
from loguru import logger
from abc import ABC, abstractmethod


class BaseCard(ABC):
    def __init__(
        self,
        title: str,
        icon: str = "",
        comment: Optional[str] = None,
        additional_content: Optional[str] = None,
    ):
        self.title = title
        self.icon = icon
        self.comment = comment
        self.additional_content = additional_content

        # 设置统一字体风格（可封装为 theme）
        # matplotlib.rcParams["font.family"] = "PingFang SC"
        matplotlib.rcParams["axes.unicode_minus"] = False

    def render_header(self):
        st.markdown(f"### {self.icon} {self.title}")

    def render_additional(self):
        if self.additional_content:
            st.markdown("---")
            st.markdown(self.additional_content)

    @abstractmethod
    def render(self):
        pass
