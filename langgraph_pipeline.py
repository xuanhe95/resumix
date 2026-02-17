from __future__ import annotations

from typing import Any, Dict, TypedDict

try:
    from langgraph.graph import END, StateGraph
except Exception as e:  # pragma: no cover - runtime dependency guard
    END = None
    StateGraph = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


class PipelineState(TypedDict, total=False):
    parse_result: str
    skills_facts_result: str
    passthrough_result: str
    summarize_experience_result: str
    build_experience_bullets_result: str
    compose_experience_result: str
    summarize_projects_result: str
    build_projects_bullets_result: str
    compose_projects_result: str
    suggest_skills_result: str
    final_json: str


def _build_graph(toolset: Any):
    if StateGraph is None:
        raise RuntimeError(
            "LangGraph is not installed. Install with: pip install langgraph"
        ) from _IMPORT_ERROR

    builder = StateGraph(PipelineState)

    builder.add_node(
        "parse_resume_sections",
        lambda _: {"parse_result": toolset.parse_resume_sections("")},
    )
    builder.add_node(
        "extract_skills_facts",
        lambda _: {"skills_facts_result": toolset.extract_skills_facts("")},
    )
    builder.add_node(
        "passthrough_base_sections",
        lambda _: {"passthrough_result": toolset.passthrough_base_sections("")},
    )
    builder.add_node(
        "summarize_experience",
        lambda _: {"summarize_experience_result": toolset.summarize_experience("")},
    )
    builder.add_node(
        "build_experience_bullets",
        lambda _: {
            "build_experience_bullets_result": toolset.build_experience_bullets("")
        },
    )
    builder.add_node(
        "compose_experience_json",
        lambda _: {"compose_experience_result": toolset.compose_experience_json("")},
    )
    builder.add_node(
        "summarize_projects",
        lambda _: {"summarize_projects_result": toolset.summarize_projects("")},
    )
    builder.add_node(
        "build_projects_bullets",
        lambda _: {"build_projects_bullets_result": toolset.build_projects_bullets("")},
    )
    builder.add_node(
        "compose_projects_json",
        lambda _: {"compose_projects_result": toolset.compose_projects_json("")},
    )
    builder.add_node(
        "suggest_missing_skills",
        lambda _: {"suggest_skills_result": toolset.suggest_missing_skills("")},
    )
    builder.add_node(
        "finalize_json",
        lambda _: {"final_json": toolset.get_final_resume_json("")},
    )

    builder.set_entry_point("parse_resume_sections")
    builder.add_edge("parse_resume_sections", "extract_skills_facts")
    builder.add_edge("extract_skills_facts", "passthrough_base_sections")
    builder.add_edge("passthrough_base_sections", "summarize_experience")
    builder.add_edge("summarize_experience", "build_experience_bullets")
    builder.add_edge("build_experience_bullets", "compose_experience_json")
    builder.add_edge("compose_experience_json", "summarize_projects")
    builder.add_edge("summarize_projects", "build_projects_bullets")
    builder.add_edge("build_projects_bullets", "compose_projects_json")
    builder.add_edge("compose_projects_json", "suggest_missing_skills")
    builder.add_edge("suggest_missing_skills", "finalize_json")
    builder.add_edge("finalize_json", END)

    return builder.compile()


def run_langgraph_pipeline(toolset: Any) -> Dict[str, Any]:
    graph = _build_graph(toolset)
    result = graph.invoke({})
    return result if isinstance(result, dict) else {}

