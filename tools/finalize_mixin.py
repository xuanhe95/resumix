from __future__ import annotations

import json

from langchain.tools import Tool


class FinalizeToolsMixin:
    def suggest_missing_skills(self, _: str) -> str:
        self._log("STEP7_SKILL_SUGGEST", "Generating additional skill suggestions...", self.COLOR_STAGE)

        exp_lines = self.state.sections.get("experience", [])
        proj_lines = self.state.sections.get("projects", [])
        source_lines = exp_lines + proj_lines

        prompt = (
            "Based on EXPERIENCE and PROJECTS text, propose additional technical stack suggestions.\n"
            "Return strict JSON only: {\"suggested_skills\": [\"...\"]}.\n"
            "Do not suggest soft skills.\n\n"
            f"EXPERIENCE_PROJECTS_TEXT:\n{json.dumps(source_lines, ensure_ascii=False)}"
        )
        raw = self.llm.generate_json(prompt)
        data = self._extract_json_obj(raw)
        llm_suggested = (
            data.get("suggested_skills", [])
            if isinstance(data.get("suggested_skills", []), list)
            else []
        )

        normalized_suggested = self._normalize_skills_from_candidates(llm_suggested + source_lines)

        existing_keys = {self._normalize_stack_key(x) for x in self.state.skill_facts}
        missing = [
            x
            for x in normalized_suggested
            if self._normalize_stack_key(x) not in existing_keys
        ]
        missing = self._dedupe(missing)

        self.state.skill_suggestions = missing
        self._log("STEP7_SKILL_SUGGEST", f"missing_skills={missing}", self.COLOR_OK)

        return json.dumps(
            {
                "existing_skills_facts": self.state.skill_facts,
                "suggested_skills_normalized": normalized_suggested,
                "missing_skills": missing,
                "missing_count": len(missing),
            },
            ensure_ascii=False,
            indent=2,
        )

    def get_final_resume_json(self, _: str) -> str:
        final_payload = {
            "personal_info": self.state.final_section_json.get("personal_info", {"items": []}),
            "education": self.state.final_section_json.get("education", {"items": []}),
            "skills": self.state.final_section_json.get("skills", {"items": []}),
            "experience": self.state.final_section_json.get("experience", {"items": []}),
            "projects": self.state.final_section_json.get("projects", {"items": []}),
            "skills_facts": self.state.skill_facts,
            "skills_to_add": self.state.skill_suggestions,
            "persistent_memory": {
                "memory_file": self.state.memory_file,
                "profile": self.state.persistent_memory,
            },
        }
        return json.dumps(final_payload, ensure_ascii=False, indent=2)

    def run_rewrite_pipeline(self, _: str) -> str:
        from langgraph_pipeline import run_langgraph_pipeline

        self._log("LANGGRAPH", "running compiled graph pipeline...", self.COLOR_STAGE)
        state = run_langgraph_pipeline(self)
        final_json = state.get("final_json", "") if isinstance(state, dict) else ""
        self._log("LANGGRAPH", "completed", self.COLOR_OK)
        return final_json or self.get_final_resume_json("")

    # Compatibility alias for older code path.
    def optimize_all(self, _: str) -> str:
        return self.run_rewrite_pipeline("")

    def optimize_section(self, section_name: str) -> str:
        section = (section_name or "").strip().lower()
        if section in {"personal_info", "education", "skills"}:
            return self.passthrough_base_sections("")
        if section == "experience":
            self.summarize_experience("")
            self.build_experience_bullets("")
            return self.compose_experience_json("")
        if section == "projects":
            self.summarize_projects("")
            self.build_projects_bullets("")
            return self.compose_projects_json("")
        return f"Section not supported: {section}"

    def as_tools(self):
        return [
            Tool(
                name="set_direction",
                func=self.set_direction,
                description="Set optimization direction. Input: target role or domain.",
            ),
            Tool(
                name="parse_resume_sections",
                func=self.parse_resume_sections,
                description="Step1: Parse resume into sections using LLM.",
            ),
            Tool(
                name="extract_skills_facts",
                func=self.extract_skills_facts,
                description=(
                    "Step2: Parse skills to JSON list with LLM and match against tech_stack_set whitelist."
                ),
            ),
            Tool(
                name="passthrough_base_sections",
                func=self.passthrough_base_sections,
                description=(
                    "Step3: Return personal_info, education, skills directly (no polishing)."
                ),
            ),
            Tool(
                name="summarize_experience",
                func=self.summarize_experience,
                description="Step4: Summarize experience into title + draft items.",
            ),
            Tool(
                name="summarize_projects",
                func=self.summarize_projects,
                description="Step4: Summarize projects into title + draft items.",
            ),
            Tool(
                name="build_experience_bullets",
                func=self.build_experience_bullets,
                description="Step5: Generate experience bullets from draft + skills and run STAR checks.",
            ),
            Tool(
                name="build_projects_bullets",
                func=self.build_projects_bullets,
                description="Step5: Generate project bullets from draft + skills and run STAR checks.",
            ),
            Tool(
                name="compose_experience_json",
                func=self.compose_experience_json,
                description="Step6: Compose final experience JSON using title/draft/bullets.",
            ),
            Tool(
                name="compose_projects_json",
                func=self.compose_projects_json,
                description="Step6: Compose final projects JSON using title/draft/bullets.",
            ),
            Tool(
                name="get_evidence_report",
                func=self.get_evidence_report,
                description=(
                    "Get evidence/fact consistency report for experience or projects."
                ),
            ),
            Tool(
                name="suggest_missing_skills",
                func=self.suggest_missing_skills,
                description=(
                    "Step7: Generate extra skill suggestions, normalize with same rules, and diff with skills facts."
                ),
            ),
            Tool(
                name="get_skill_memory",
                func=self.get_skill_memory,
                description="Show short-term skills memory extracted from skills section.",
            ),
            Tool(
                name="get_sections_overview",
                func=self.get_sections_overview,
                description="Get parsed section item counts in JSON.",
            ),
            Tool(
                name="get_persistent_memory",
                func=self.get_persistent_memory,
                description="Show persistent user memory profile.",
            ),
            Tool(
                name="update_persistent_memory",
                func=self.update_persistent_memory,
                description=(
                    "Update persistent memory via JSON patch or plain feedback text."
                ),
            ),
            Tool(
                name="clear_persistent_memory",
                func=self.clear_persistent_memory,
                description="Clear persistent memory and reset to defaults.",
            ),
            Tool(
                name="run_rewrite_pipeline",
                func=self.run_rewrite_pipeline,
                description="Run full deterministic pipeline and return final resume JSON.",
            ),
            Tool(
                name="get_final_resume_json",
                func=self.get_final_resume_json,
                description="Get final assembled resume JSON.",
            ),
            Tool(
                name="optimize_all",
                func=self.optimize_all,
                description="Compatibility alias to run full pipeline.",
            ),
            Tool(
                name="optimize_section",
                func=self.optimize_section,
                description="Compatibility section runner for experience/projects/base sections.",
            ),
        ]
