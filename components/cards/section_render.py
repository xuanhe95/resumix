import json
import streamlit as st
from typing import Any, Dict, List
from section.section_base import SectionBase
import re
from utils.logger import logger


class SectionRender:

    def render_section(self, section: SectionBase):
        """根据 section 名称渲染不同格式的 JSON 内容"""
        section_json = section.rewritten_text
        section_name = section.name
        try:
            section_json = self._strip_markdown_code_fence(section_json)
            data = json.loads(section_json)
        except json.JSONDecodeError:
            st.warning("⚠️ JSON 解析失败，原始数据如下：")
            st.code(section_json)
            return

        if section_name == "personal_info":
            self._render_basics(data)
        elif section_name == "education":
            self._render_education(data.get("education", []))
        elif section_name == "experience":
            self._render_work(data.get("work", []))
        elif section_name == "projects":
            self._render_projects(data.get("projects", []))
        elif section_name == "skills":
            self._render_skills(data.get("skills", []))
        else:
            st.json(data)  # fallback

    @staticmethod
    def _strip_markdown_code_fence(text: str) -> str:
        # 清除 markdown code block 头尾
        lines = text.strip().splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _render_basics(self, basics: Dict[str, Any]):
        st.markdown(f"### 👤 {basics.get('name', '匿名')}")
        st.markdown(f"📧 {basics.get('email', '')} | 📱 {basics.get('phone', '')}")
        st.markdown(f"🌐 [{basics.get('website', '')}]({basics.get('website', '')})")
        st.markdown(f"📍 {basics.get('address', '')}")

    def _render_education(self, education_items: List[Dict[str, Any]]):
        for edu in education_items:
            st.markdown(
                f"### 🎓 {edu.get('institution', '')} - {edu.get('studyType', '')}"
            )
            st.markdown(
                f"{edu.get('area', '')} | {edu.get('location', '')} | {edu.get('startDate', '')} - {edu.get('endDate', '')}"
            )
            if edu.get("score"):
                st.markdown(f"GPA: {edu['score']}")
            if edu.get("additionalAreas"):
                st.markdown("**相关课程：** " + ", ".join(edu["additionalAreas"]))
            st.markdown("---")

    def _render_work(self, work_items: List[Dict[str, Any]]):
        for job in work_items:
            st.markdown(f"### 🏢 {job.get('company', '')} - {job.get('position', '')}")
            st.markdown(
                f"📍 {job.get('location', '')} | {job.get('startDate', '')} - {job.get('endDate', '')}"
            )
            if job.get("highlights"):
                for h in job["highlights"]:
                    st.markdown(f"- {h}")
            st.markdown("---")

    def _render_projects(self, projects: List[Dict[str, Any]]):
        for proj in projects:
            st.markdown(f"### 💡 {proj.get('name', '')}")
            st.markdown(f"{proj.get('description', '')}")
            if proj.get("keywords"):
                st.markdown(
                    "**关键词：** " + ", ".join([f"`{kw}`" for kw in proj["keywords"]])
                )
            if proj.get("url"):
                st.markdown(f"🔗 [项目链接]({proj['url']})")
            st.markdown("---")

    def _render_skills(self, skills: List[Dict[str, Any]]):
        ICON_MAP = {
            "Programming Languages": "🧠",
            "Tools": "🛠️",
            "Frameworks": "📚",
            "Computer Proficiency": "🧩",
            "Soft Skills": "💬",
            "Communication": "💬",
            "Leadership": "🎯",
            "Creativity": "✨",
            "Problem Solving": "🧠",
            "Team Work": "👥",
        }

        for skill_group in skills:
            name = skill_group.get("name", "其他技能")
            icon = ICON_MAP.get(name, "🔧")
            keywords = skill_group.get("keywords", [])

            st.markdown(f"**{icon} {name}**")
            st.markdown(" ".join([f"`{kw}`" for kw in keywords]))
            st.markdown("---")
