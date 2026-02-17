from __future__ import annotations

import json
import re
from typing import Dict, List, Optional


class SummaryToolsMixin:
    @staticmethod
    def _is_probable_title_line(section: str, line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        sl = s.lower()

        # Most bullet sentences end with punctuation; treat them as content, not title.
        if s.endswith((".", ";", "。", "；")):
            return False

        # common date-only lines should not be title lines
        if re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|present)\b",
            sl,
        ) and len(s.split()) <= 8:
            return False

        # Metric-heavy lines are usually bullet content.
        if (re.search(r"\d|%", s) and len(s.split()) >= 6) or len(s) >= 110:
            return False

        action_verbs = (
            "built",
            "designed",
            "implemented",
            "developed",
            "optimized",
            "led",
            "created",
            "delivered",
            "improved",
            "reduced",
            "increased",
            "launched",
            "migrated",
            "automated",
            "provided",
            "set",
            "set up",
            "ensured",
            "refactored",
            "integrated",
            "utilized",
            "achieved",
            "supported",
            "maintained",
        )
        if any(sl.startswith(v + " ") for v in action_verbs):
            return False

        # section-specific heuristics
        if section == "experience":
            if "," in s and len(s.split()) <= 22:
                return True
            if " - " in s and len(s.split()) <= 22:
                return True
            return False

        if section == "projects":
            if " - " in s or "[" in s or "http" in sl:
                return True
            if len(s.split()) <= 16 and s[0].isupper() and not s.endswith("."):
                return True
            return False

        return False

    def _fallback_summaries(self, section: str, lines: List[str]) -> List[Dict[str, str]]:
        """
        Deterministic grouping that preserves all parsed lines.
        Used as seed summaries and as safety fallback.
        """
        groups: List[Dict[str, List[str]]] = []
        current: Optional[Dict[str, List[str]]] = None

        for ln in lines:
            text = str(ln).strip()
            if not text:
                continue
            if self._is_probable_title_line(section, text):
                if current is not None:
                    groups.append(current)
                current = {"title": [text], "body": []}
            else:
                if current is None:
                    current = {"title": [], "body": []}
                current["body"].append(text)

        if current is not None:
            groups.append(current)

        out: List[Dict[str, str]] = []
        for i, g in enumerate(groups, start=1):
            title_raw = " ".join(g.get("title", [])).strip()
            body_lines = g.get("body", [])
            if not title_raw:
                if body_lines:
                    title_raw = " ".join(body_lines[0].split()[:8]).strip()
                else:
                    title_raw = f"{section.title()} Item {i}"

            draft_src = body_lines if body_lines else [title_raw]
            draft_raw = " ".join(draft_src).strip()
            if len(draft_raw) > 320:
                draft_raw = draft_raw[:317].rstrip() + "..."

            out.append({"title": title_raw, "draft": draft_raw})

        return out

    def summarize_section(self, section_name: str) -> str:
        section = (section_name or "").strip().lower()
        if section not in {"experience", "projects"}:
            return '{"error":"section must be experience or projects"}'
        lines = self.state.sections.get(section, [])
        if not lines:
            self._log(
                f"STEP4_SUMMARY_{section.upper()}",
                "no parsed content for this section",
                self.COLOR_ERR,
            )
            return json.dumps({"section": section, "items": []}, ensure_ascii=False)

        self._log(
            f"STEP4_SUMMARY_{section.upper()}",
            "Generating title+draft summaries...",
            self.COLOR_STAGE,
        )
        seed_items = self._fallback_summaries(section, lines)
        self._log(
            f"STEP4_SUMMARY_{section.upper()}",
            f"seed_items={len(seed_items)}",
            self.COLOR_DATA,
        )
        prompt = (
            f"You are summarizing resume {section}.\n"
            "Rewrite seed items into cleaner title+draft summaries.\n"
            "You must preserve item count and order exactly.\n"
            "Return strict JSON only:\n"
            "{\"items\":[{\"title\":\"...\",\"draft\":\"...\"}]}\n"
            "Do not invent facts.\n\n"
            f"SEED_ITEMS_COUNT={len(seed_items)}\n"
            f"SEED_ITEMS:\n{json.dumps(seed_items, ensure_ascii=False)}\n\n"
            f"{self._memory_prompt_block()}\n"
        )
        raw = self.llm.generate_json(prompt)
        data = self._extract_json_obj(raw)
        items = data.get("items", []) if isinstance(data.get("items", []), list) else []

        parsed: List[Dict[str, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title", "")).strip()
            draft = str(it.get("draft", "")).strip()
            if not title and draft:
                title = " ".join(draft.split()[:8]).strip()
            if title or draft:
                parsed.append({"title": title, "draft": draft})

        if not parsed:
            # LLM repair pass: force JSON schema from first raw response.
            repair_content = self._prepare_repair_content(raw, limit=1200)
            if repair_content:
                repair_prompt = (
                    "Convert the following content into strict JSON:\n"
                    "{\"items\":[{\"title\":\"...\",\"draft\":\"...\"}]}\n"
                    "Do not add new facts.\n\n"
                    f"CONTENT:\n{repair_content}"
                )
                repair_raw = self.llm.generate_json(repair_prompt)
                repair_data = self._extract_json_obj(repair_raw)
                repair_items = (
                    repair_data.get("items", [])
                    if isinstance(repair_data.get("items", []), list)
                    else []
                )
                for it in repair_items:
                    if not isinstance(it, dict):
                        continue
                    title = str(it.get("title", "")).strip()
                    draft = str(it.get("draft", "")).strip()
                    if not title and draft:
                        title = " ".join(draft.split()[:8]).strip()
                    if title or draft:
                        parsed.append({"title": title, "draft": draft})
            else:
                self._log(
                    f"STEP4_SUMMARY_{section.upper()}",
                    "skip repair prompt due noisy/empty raw output",
                    self.COLOR_WARN,
                )

        if len(parsed) != len(seed_items):
            self._log(
                f"STEP4_SUMMARY_{section.upper()}",
                (
                    f"LLM items mismatch expected={len(seed_items)} got={len(parsed)}; "
                    "auto-completing with seed items"
                ),
                self.COLOR_WARN,
            )

        # Always preserve full coverage using seed items as baseline.
        merged: List[Dict[str, str]] = []
        for idx, seed in enumerate(seed_items):
            if idx < len(parsed):
                title = str(parsed[idx].get("title", "")).strip() if isinstance(parsed[idx], dict) else ""
                draft = str(parsed[idx].get("draft", "")).strip() if isinstance(parsed[idx], dict) else ""
                merged.append(
                    {
                        "title": title or seed.get("title", ""),
                        "draft": draft or seed.get("draft", ""),
                    }
                )
            else:
                merged.append(seed)

        self.state.section_summaries[section] = merged
        self._log(
            f"STEP4_SUMMARY_{section.upper()}",
            f"items={len(merged)}",
            self.COLOR_OK,
        )
        return json.dumps({"section": section, "items": merged}, ensure_ascii=False, indent=2)

    def summarize_experience(self, _: str) -> str:
        return self.summarize_section("experience")

    def summarize_projects(self, _: str) -> str:
        return self.summarize_section("projects")
