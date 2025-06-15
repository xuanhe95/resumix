import streamlit as st
from job_parser.resume_parser import ResumeParser
from utils.logger import logger
from typing import Dict, Optional
from components.cards.base_card import BaseCard


class AgentCard(BaseCard):
    def __init__(
        self,
        title: str = "AI Agent",
        icon: str = "🤖",
        comment: Optional[str] = None,
        additional_content: Optional[str] = None,
    ):
        super().__init__(
            title=title,
            icon=icon,
            comment=comment,
            additional_content=additional_content
        )
        self.parser = ResumeParser()
        
    def render_agent_response(self, result: str):
        st.chat_message("Resumix").write(result)
        
    def render_agent_interaction(self, text: str, jd_content: str, agent):
        sections = self.parser.parse_resume(text)
        for section, content in sections.items():
            prompt = f"""你是一个简历优化助手。请参考以下岗位描述，并优化简历内容：

                岗位描述：{jd_content}

                简历原文：
\"\"\"{content}\"\"\"

请按照如下格式作答：
Thought: ...
Action: local_llm_generate
Action Input: \"\"\"优化后的内容\"\"\"
"""
            result = agent.run(prompt)
            self.render_agent_response(result)
    
    def render(self):
        self.render_header()
        if self.comment:
            self.render_comment()
        self.render_additional()


def agent_card(text: str):
    """Legacy function wrapper for backward compatibility"""
    logger.info("Handling Resume Agent with provided resume text.")
    card = AgentCard()
    card.render()


def handle_agent(text: str, jd_content: str, agent):
    """Legacy function wrapper for backward compatibility"""
    logger.info("Handling AI Agent with provided resume text and job description content.")
    card = AgentCard()
    card.render()
    card.render_agent_interaction(text, jd_content, agent)