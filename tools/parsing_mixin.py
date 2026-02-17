from __future__ import annotations

import json
from typing import Dict, List

from resume_io import normalize_sections, parse_sections_by_llm


class ParsingToolsMixin:
    def get_sections_overview(self, _: str) -> str:
        if not self.state.sections:
            return "{}"
        summary = {k: len(v) for k, v in self.state.sections.items()}
        return json.dumps(summary, ensure_ascii=False)

    def parse_resume_sections(self, _: str) -> str:
        if not self.state.resume_text.strip():
            return '{"error":"No resume text provided"}'

        self._log("STEP1_PARSE", "LLM classifying resume into sections...", self.COLOR_STAGE)
        sections = parse_sections_by_llm(self.state.resume_text, self.llm)
        self.state.sections = normalize_sections(sections)

        keys = [k for k, v in self.state.sections.items() if v]
        counts = {k: len(v) for k, v in self.state.sections.items()}
        self._log("STEP1_PARSE", f"done sections={keys}", self.COLOR_OK)
        self._log("STEP1_PARSE", f"counts={counts}", self.COLOR_DATA)
        for sec in ["personal_info", "education", "skills", "experience", "projects"]:
            if not self.state.sections.get(sec):
                self._log(
                    "STEP1_PARSE",
                    f"section '{sec}' parsed as empty",
                    self.COLOR_ERR,
                )

        return json.dumps({"sections": keys, "counts": counts}, ensure_ascii=False, indent=2)

    def extract_skills_facts(self, _: str) -> str:
        self._log("STEP2_SKILLS_FACTS", "Extracting skills JSON and matching whitelist...", self.COLOR_STAGE)
        skills_lines = self.state.sections.get("skills", [])
        if not skills_lines:
            self.state.skill_facts = []
            self.state.skill_memory = []
            self.state.facts["skills"] = {"hard_facts": [], "soft_facts": []}
            self._log("STEP2_SKILLS_FACTS", "skills section is empty", self.COLOR_WARN)
            return json.dumps({"skills_facts": []}, ensure_ascii=False)

        prompt = (
            "Extract only concrete technical stack items from SKILLS text.\n"
            "Return strict JSON only: {\"skills\": [\"...\"]}.\n"
            "Do not invent any skill not present in SKILLS text.\n\n"
            "SKILLS_TEXT:\n" + "\n".join(skills_lines)
        )
        raw = self.llm.generate_json(prompt)
        data = self._extract_json_obj(raw)
        llm_skills = data.get("skills", []) if isinstance(data.get("skills", []), list) else []

        normalized = self._normalize_skills_from_candidates(llm_skills + skills_lines)
        self.state.skill_facts = normalized
        self.state.skill_memory = list(normalized)
        self.state.facts["skills"] = {"hard_facts": [], "soft_facts": list(normalized)}

        self._log("STEP2_SKILLS_FACTS", f"skills_facts={normalized}", self.COLOR_OK)
        return json.dumps(
            {
                "skills_facts": normalized,
                "count": len(normalized),
            },
            ensure_ascii=False,
            indent=2,
        )

    def get_skill_memory(self, _: str) -> str:
        return json.dumps(
            {
                "skill_memory": self.state.skill_memory,
                "count": len(self.state.skill_memory),
            },
            ensure_ascii=False,
            indent=2,
        )

    def passthrough_base_sections(self, _: str) -> str:
        self._log(
            "STEP3_BASE_SECTIONS",
            "Returning personal_info / education / skills without polishing...",
            self.COLOR_STAGE,
        )
        result: Dict[str, Dict[str, List[str]]] = {}
        for section in ["personal_info", "education", "skills"]:
            lines = self.state.sections.get(section, [])
            self.state.final_section_json[section] = {"section": section, "items": list(lines)}
            self.state.rewritten_sections[section] = "\n".join(f"- {x}" for x in lines)
            result[section] = {"items": list(lines)}

        self._log("STEP3_BASE_SECTIONS", "done", self.COLOR_OK)
        return json.dumps(result, ensure_ascii=False, indent=2)

