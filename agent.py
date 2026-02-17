from __future__ import annotations

from langchain.agents import AgentType, initialize_agent

from tools import ResumeAgentTools


def build_agent(llm_wrapper, toolset: ResumeAgentTools):
    return initialize_agent(
        tools=toolset.as_tools(),
        llm=llm_wrapper,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        max_iterations=4,
        agent_kwargs={
            "prefix": (
                "You are a strict ReAct resume assistant.\n"
                "Rules:\n"
                "1) Never fabricate resume content, names, emails, companies, dates.\n"
                "2) Never put full resume text into Action Input for parse_resume_sections.\n"
                "3) For parse_resume_sections, Action Input must be empty string.\n"
                "4) Never output Observation yourself; Observation comes from tool result only.\n"
                "5) If uncertain, call get_sections_overview first.\n"
            )
        },
    )
