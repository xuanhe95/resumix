#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agent import build_agent
from langgraph_pipeline import run_langgraph_pipeline
from langchain_adapter import LLMWrapper
from llm_caller import LLMClient
from record_exporter import RecordExporter
from resume_io import ResumeState, read_pdf_text
from resume_report import ResumeReportPrinter
from tools import ResumeAgentTools


SECTION_COLORS = {
    "personal_info": "\033[95m",  # magenta
    "education": "\033[96m",  # cyan
    "experience": "\033[92m",  # green
    "projects": "\033[94m",  # blue
    "skills": "\033[93m",  # yellow
}
COLOR_RESET = "\033[0m"
COLOR_HEADER = "\033[96m"
COLOR_WARN = "\033[93m"


def _print_step_header(title: str) -> None:
    print(f"\n{COLOR_HEADER}=== {title} ==={COLOR_RESET}")


def _print_section_outputs(state: ResumeState) -> None:
    _print_step_header("Final Rewritten Sections")
    for sec in ["personal_info", "education", "skills", "experience", "projects"]:
        if sec not in state.rewritten_sections:
            continue
        color = SECTION_COLORS.get(sec, "\033[97m")
        print(f"\n{color}[{sec}]{COLOR_RESET}")
        print(f"{color}{state.rewritten_sections[sec]}{COLOR_RESET}")


def _group_original_complex_items(toolset: ResumeAgentTools, section: str) -> List[Dict[str, Any]]:
    lines = toolset.state.sections.get(section, [])
    groups: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for line in lines:
        text = str(line).strip()
        if not text:
            continue
        if toolset._is_probable_title_line(section, text):
            if current and (current.get("title") or current.get("bullets")):
                groups.append(current)
            current = {"title": text, "bullets": []}
        else:
            if current is None:
                current = {"title": "", "bullets": []}
            current["bullets"].append(text)

    if current and (current.get("title") or current.get("bullets")):
        groups.append(current)

    items: List[Dict[str, Any]] = []
    for idx, g in enumerate(groups, start=1):
        title = str(g.get("title", "")).strip() or f"{section.title()} Item {idx}"
        bullets = [str(x).strip() for x in g.get("bullets", []) if str(x).strip()]
        draft = " ".join(bullets).strip()
        if len(draft) > 420:
            draft = draft[:417].rstrip() + "..."
        items.append({"title": title, "draft": draft, "bullets": bullets})

    if not items:
        # Fallback to previously summarized items if grouping fails.
        for idx, it in enumerate(toolset.state.section_summaries.get(section, []), start=1):
            if not isinstance(it, dict):
                continue
            title = str(it.get("title", "")).strip() or f"{section.title()} Item {idx}"
            draft = str(it.get("draft", "")).strip()
            items.append({"title": title, "draft": draft, "bullets": []})

    return items


def _build_original_payload(toolset: ResumeAgentTools) -> Dict[str, Any]:
    return {
        "personal_info": {"items": list(toolset.state.sections.get("personal_info", []))},
        "education": {"items": list(toolset.state.sections.get("education", []))},
        "skills": {"items": list(toolset.state.sections.get("skills", []))},
        "experience": {"items": _group_original_complex_items(toolset, "experience")},
        "projects": {"items": _group_original_complex_items(toolset, "projects")},
    }


def main() -> int:
    # Always load env from this standalone folder to avoid picking root .env by mistake.
    env_path = Path(__file__).with_name(".env")
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"[ENV] loaded={env_path}", flush=True)

    parser = argparse.ArgumentParser(description="Standalone Resume Rewrite Pipeline")
    parser.add_argument("--resume", required=True, help="Absolute path to resume PDF")
    parser.add_argument("--direction", default="General", help="Target role/direction")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    resume_path = str(Path(args.resume).expanduser().resolve())
    max_pages = int(os.getenv("RESUME_MAX_PAGES", "6"))
    text = read_pdf_text(resume_path, max_pages=max_pages)

    _print_step_header("PDF Read")
    print(text)
    print(f"\n[DEBUG] resume_text_chars={len(text)} max_pages={max_pages}")
    if not text.strip():
        print(
            "[ERROR] Extracted resume text is empty. "
            "This usually means the PDF is image-only/scanned or the file path is wrong."
        )
        return 1

    state = ResumeState(
        resume_path=resume_path,
        resume_text=text,
        target_direction=args.direction,
    )

    client = LLMClient()
    llm = LLMWrapper(client=client)
    toolset = ResumeAgentTools(state=state, llm=client)
    agent = build_agent(llm, toolset)

    _print_step_header("Deterministic Pipeline")
    print(toolset.set_direction(args.direction))
    _print_step_header("LangGraph Orchestration")
    try:
        graph_state = run_langgraph_pipeline(toolset)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        print("Install dependency: pip install langgraph")
        return 1

    for key in [
        "parse_result",
        "skills_facts_result",
        "passthrough_result",
        "summarize_experience_result",
        "build_experience_bullets_result",
        "compose_experience_result",
        "summarize_projects_result",
        "build_projects_bullets_result",
        "compose_projects_result",
        "suggest_skills_result",
    ]:
        val = graph_state.get(key, "")
        if val:
            print(val)

    final_json = graph_state.get("final_json", "") or toolset.get_final_resume_json("")
    _print_step_header("Final Resume JSON")
    print(final_json)

    # Save final JSON record under records/ using profile name + timestamp.
    try:
        final_payload = json.loads(final_json)
        if not isinstance(final_payload, dict):
            final_payload = {"final_json_raw": final_json}
    except Exception:
        final_payload = {"final_json_raw": final_json}

    record_path = ""
    save_record = os.getenv("SAVE_FINAL_RECORD", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if save_record:
        records_dir = os.getenv(
            "RECORDS_DIR",
            str(Path(__file__).with_name("records")),
        )
        profile_name = RecordExporter.derive_profile_name(
            memory_profile=state.persistent_memory if isinstance(state.persistent_memory, dict) else {},
            target_direction=state.target_direction,
            fallback_user_id=os.getenv("USER_MEMORY_USER_ID", "default"),
        )
        exporter = RecordExporter(records_dir=records_dir)
        record_path = exporter.save_final_json(final_payload, profile_name=profile_name)
        _print_step_header("Record Saved")
        print(record_path)

    _print_step_header("Resume Report")
    report_printer = ResumeReportPrinter()
    original_payload = _build_original_payload(toolset)
    report_printer.print_report(
        final_payload,
        record_path=record_path,
        original_payload=original_payload,
    )

    _print_step_header("Suggested Skills To Add")
    if state.skill_suggestions:
        for s in state.skill_suggestions:
            print(f"{COLOR_WARN}- {s}{COLOR_RESET}")
    else:
        print(f"{COLOR_WARN}No additional skill suggestions.{COLOR_RESET}")

    if args.interactive:
        _print_step_header("Interactive Mode")
        print(
            "Commands:\n"
            "  parse\n"
            "  skills_facts\n"
            "  passthrough\n"
            "  summarize <experience|projects>\n"
            "  bullets <experience|projects>\n"
            "  compose <experience|projects>\n"
            "  evidence <experience|projects>\n"
            "  memory_show\n"
            "  memory_update <json_or_text>\n"
            "  memory_clear\n"
            "  suggest_skills\n"
            "  skill_memory\n"
            "  sections\n"
            "  run_pipeline\n"
            "  final_json\n"
            "  agent: <free text>\n"
            "  exit\n"
        )
        while True:
            q = input("\nYou> ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            if not q:
                continue

            if q.lower() == "parse":
                print(toolset.parse_resume_sections(""))
                continue
            if q.lower() == "skills_facts":
                print(toolset.extract_skills_facts(""))
                continue
            if q.lower() == "passthrough":
                print(toolset.passthrough_base_sections(""))
                continue
            if q.lower().startswith("summarize "):
                sec = q[len("summarize ") :].strip()
                print(toolset.summarize_section(sec))
                continue
            if q.lower().startswith("bullets "):
                sec = q[len("bullets ") :].strip()
                print(toolset.build_section_bullets(sec))
                continue
            if q.lower().startswith("compose "):
                sec = q[len("compose ") :].strip()
                print(toolset.compose_section_json(sec))
                continue
            if q.lower().startswith("evidence "):
                sec = q[len("evidence ") :].strip()
                print(toolset.get_evidence_report(sec))
                continue
            if q.lower() == "memory_show":
                print(toolset.get_persistent_memory(""))
                continue
            if q.lower().startswith("memory_update "):
                payload = q[len("memory_update ") :].strip()
                print(toolset.update_persistent_memory(payload))
                continue
            if q.lower() == "memory_clear":
                print(toolset.clear_persistent_memory(""))
                continue
            if q.lower() == "suggest_skills":
                print(toolset.suggest_missing_skills(""))
                continue
            if q.lower() == "skill_memory":
                print(toolset.get_skill_memory(""))
                continue
            if q.lower() == "sections":
                print(toolset.get_sections_overview(""))
                continue
            if q.lower() == "run_pipeline":
                try:
                    result = run_langgraph_pipeline(toolset)
                    print(result.get("final_json", toolset.get_final_resume_json("")))
                except RuntimeError as e:
                    print(f"[ERROR] {e}")
                continue
            if q.lower() == "final_json":
                print(toolset.get_final_resume_json(""))
                continue

            if q.lower().startswith("agent:"):
                agent_q = q.split(":", 1)[1].strip()
                r = agent.invoke({"input": agent_q})
                print("\n=== Agent Intermediate Steps ===")
                for i, step in enumerate(r.get("intermediate_steps", []), start=1):
                    action, observation = step
                    print(f"\n[Step {i}] tool={getattr(action, 'tool', '')}")
                    print(f"tool_input={getattr(action, 'tool_input', '')}")
                    print(f"observation={str(observation)[:1200]}")
                print("\nAgent>")
                print(r.get("output", ""))
                continue

            print(
                "Unknown command. Use: parse | skills_facts | passthrough | "
                "summarize <experience|projects> | bullets <experience|projects> | "
                "compose <experience|projects> | evidence <experience|projects> | "
                "memory_show | memory_update <json_or_text> | memory_clear | "
                "suggest_skills | skill_memory | sections | "
                "run_pipeline | final_json | agent: <text>"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
