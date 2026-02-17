from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from best_of_n import BestOfNSelector


class BulletsToolsMixin:
    @staticmethod
    def _star_check(bullet: str) -> Dict[str, object]:
        b = (bullet or "").strip()
        words = b.split()
        first = words[0].lower() if words else ""

        action_verbs = {
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
        }
        result_words = {
            "improved",
            "reduced",
            "increased",
            "boosted",
            "saved",
            "achieved",
            "cut",
            "faster",
            "latency",
            "throughput",
            "reliability",
            "uptime",
        }

        has_action = first in action_verbs or any(v in b.lower() for v in action_verbs)
        has_task = len(words) >= 10
        has_result = bool(re.search(r"\d|%", b)) or any(w in b.lower() for w in result_words)

        score = int(has_action) + int(has_task) + int(has_result)
        passed = score >= 2 and has_action
        return {
            "passed": passed,
            "score": score,
            "has_action": has_action,
            "has_task_context": has_task,
            "has_result": has_result,
        }

    def _revise_bullet_with_star(
        self,
        section: str,
        title: str,
        draft: str,
        bullet: str,
        skill_memory: List[str],
        original_lines: List[str],
    ) -> str:
        original = (bullet or "").strip()
        if not original:
            return original

        prompt = (
            f"You are revising one resume bullet for section: {section}.\n"
            "Improve it to better satisfy STAR style while keeping facts faithful.\n"
            "Return strict JSON only: {\"revised_bullet\":\"...\"}\n"
            "Rules:\n"
            "1) Do not invent any facts not present in provided context.\n"
            "2) Keep concise resume-bullet style.\n"
            "3) Prefer action verb start and include outcome where available.\n"
            "4) Emphasize concrete usage of listed skills only when truthful.\n\n"
            f"Title: {title}\n"
            f"Draft: {draft}\n"
            f"Skill memory: {json.dumps(skill_memory, ensure_ascii=False)}\n"
            f"Original section bullets: {json.dumps(original_lines, ensure_ascii=False)}\n"
            f"Current bullet: {original}\n\n"
            f"{self._memory_prompt_block()}\n"
        )
        raw = self.llm.generate_json(prompt)
        data = self._extract_json_obj(raw)
        revised = str(data.get("revised_bullet", "")).strip() if isinstance(data, dict) else ""
        if not revised:
            return original

        before = self._star_check(original)
        after = self._star_check(revised)
        # Keep revised only when quality does not regress.
        if int(after.get("score", 0)) < int(before.get("score", 0)):
            return original
        return revised

    def _build_bullet_reviews(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        bullets: List[str],
        skill_memory: List[str],
        original_lines: List[str],
    ) -> Tuple[List[str], List[Dict[str, object]], int]:
        final_bullets: List[str] = []
        bullet_reviews: List[Dict[str, object]] = []
        revised_count = 0

        for b in bullets:
            before = self._star_check(b)
            revised = b
            if not bool(before.get("passed", False)):
                revised = self._revise_bullet_with_star(
                    section=section,
                    title=title,
                    draft=draft,
                    bullet=b,
                    skill_memory=skill_memory,
                    original_lines=original_lines,
                )
                if revised != b:
                    revised_count += 1

            after = self._star_check(revised)
            final_bullets.append(revised)
            bullet_reviews.append(
                {
                    "bullet_original": b,
                    "bullet_revised": revised,
                    "used_revised": revised != b,
                    "star_original": before,
                    "star_revised": after,
                }
            )

        return final_bullets, bullet_reviews, revised_count

    def _evaluate_item_evidence(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        bullets: List[str],
        original_lines: List[str],
    ) -> Dict[str, object]:
        return self.evidence_critic.evaluate_item(
            section=section,
            title=title,
            draft=draft,
            bullets=bullets,
            source_lines=original_lines,
            skill_facts=self.state.skill_facts,
        )

    def _build_item_payload(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        final_bullets: List[str],
        bullet_reviews: List[Dict[str, object]],
        candidate_selection: Optional[Dict[str, object]],
        original_lines: List[str],
    ) -> Dict[str, object]:
        evidence_result = self._evaluate_item_evidence(
            section=section,
            title=title,
            draft=draft,
            bullets=final_bullets,
            original_lines=original_lines,
        )
        evidence_reports = (
            evidence_result.get("bullet_reports", [])
            if isinstance(evidence_result.get("bullet_reports", []), list)
            else []
        )

        # Merge STAR + evidence check per bullet for easier review.
        merged_bullet_reports: List[Dict[str, object]] = []
        for idx, sr in enumerate(bullet_reviews):
            row = dict(sr) if isinstance(sr, dict) else {"star_revised": {}, "star_original": {}}
            er = evidence_reports[idx] if idx < len(evidence_reports) and isinstance(evidence_reports[idx], dict) else {}
            row["evidence"] = {
                "passed": bool(er.get("passed", False)),
                "support_score": er.get("support_score", 0.0),
                "consistency_score": er.get("consistency_score", 0.0),
                "reason": er.get("reason", ""),
                "evidence_refs": er.get("evidence_refs", []),
                "missing_numeric_tokens": er.get("missing_numeric_tokens", []),
                "matched_skills": er.get("matched_skills", []),
                "unsupported_skill_terms": er.get("unsupported_skill_terms", []),
            }
            merged_bullet_reports.append(row)

        payload: Dict[str, object] = {
            "title": title,
            "draft": draft,
            "bullets": final_bullets,
            "bullet_reviews": merged_bullet_reports,
            "evidence_summary": evidence_result.get("summary", {}),
        }
        if isinstance(candidate_selection, dict) and candidate_selection:
            payload["candidate_selection"] = candidate_selection
        return payload

    def _generate_item_from_draft_once(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        skill_memory: List[str],
        original_lines: List[str],
        variant_idx: int,
        variant_count: int,
        variation_hint: str,
    ) -> Dict[str, object]:
        prompt = (
            f"You are rewriting one resume item in section: {section}.\n"
            f"Generate candidate variant {variant_idx}/{variant_count}.\n"
            "Return strict JSON only:\n"
            "{\"title\":\"...\",\"draft\":\"...\",\"bullets\":[\"...\",\"...\"]}\n"
            "Rules:\n"
            "1) Do not invent facts.\n"
            "2) Keep title concise and concrete.\n"
            "3) Draft should be 1-2 concise sentences.\n"
            "4) Bullets should be STAR style where possible.\n"
            "5) Emphasize listed skills only when truthful.\n\n"
            f"STYLE_HINT:\n{variation_hint}\n\n"
            f"INPUT_TITLE:\n{title}\n\n"
            f"INPUT_DRAFT:\n{draft}\n\n"
            f"SKILL_MEMORY:\n{json.dumps(skill_memory, ensure_ascii=False)}\n\n"
            f"ORIGINAL_SECTION_LINES:\n{json.dumps(original_lines, ensure_ascii=False)}\n\n"
            f"{self._memory_prompt_block()}\n"
        )
        raw = self.llm.generate_json(prompt)
        data = self._extract_json_obj(raw)
        if not data:
            return {
                "title": title,
                "draft": draft,
                "bullets": [],
            }

        item_title = str(data.get("title", "")).strip() if isinstance(data, dict) else ""
        item_draft = str(data.get("draft", "")).strip() if isinstance(data, dict) else ""
        bullets = data.get("bullets", []) if isinstance(data, dict) and isinstance(data.get("bullets", []), list) else []
        clean_bullets = [str(b).strip() for b in bullets if str(b).strip()]
        return {
            "title": item_title or title,
            "draft": item_draft or draft,
            "bullets": clean_bullets,
        }

    def _generate_item_from_draft(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        skill_memory: List[str],
        original_lines: List[str],
    ) -> Dict[str, object]:
        """
        Best-of-N generation for one item:
        - generate N candidates with LLM
        - score candidates via deterministic ranker
        - return best candidate + score report
        """
        best_enabled = os.getenv("BEST_OF_N_ENABLED", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        try:
            n = int(os.getenv("BULLET_CANDIDATE_COUNT", "3").strip() or "3")
        except Exception:
            n = 3
        candidate_count = max(1, min(5, n if best_enabled else 1))

        style_hints = [
            "Highlight measurable impact and outcome first.",
            "Highlight architecture and design decisions first.",
            "Highlight reliability/performance improvements first.",
            "Highlight ownership and execution complexity first.",
            "Highlight system scale and engineering trade-offs first.",
        ]

        candidates: List[Dict[str, object]] = []
        for i in range(candidate_count):
            hint = style_hints[i % len(style_hints)]
            item = self._generate_item_from_draft_once(
                section=section,
                title=title,
                draft=draft,
                skill_memory=skill_memory,
                original_lines=original_lines,
                variant_idx=i + 1,
                variant_count=candidate_count,
                variation_hint=hint,
            )
            candidates.append(item)

        selector = BestOfNSelector(skill_memory=skill_memory, original_lines=original_lines)
        best_item, report = selector.select(candidates)
        best_item = dict(best_item)
        best_item["candidate_selection"] = report
        return best_item

    def build_section_bullets(self, section_name: str) -> str:
        section = (section_name or "").strip().lower()
        if section not in {"experience", "projects"}:
            return '{"error":"section must be experience or projects"}'

        summaries = self.state.section_summaries.get(section, [])
        if not summaries:
            self.summarize_section(section)
            summaries = self.state.section_summaries.get(section, [])

        if not summaries:
            self._log(
                f"STEP5_BULLETS_{section.upper()}",
                "no summary items; bullets remain empty",
                self.COLOR_ERR,
            )
            return json.dumps({"section": section, "items": []}, ensure_ascii=False)

        self._log(
            f"STEP5_BULLETS_{section.upper()}",
            "Generating STAR-style bullets from drafts + skills memory...",
            self.COLOR_STAGE,
        )

        skill_memory = self.state.skill_memory
        original_lines = self.state.sections.get(section, [])
        force_draft_mode = os.getenv("BULLETS_FROM_DRAFT_ONLY", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        best_of_n_enabled = os.getenv("BEST_OF_N_ENABLED", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        use_per_item_generation = force_draft_mode or best_of_n_enabled

        if use_per_item_generation:
            mode_msg = (
                "BULLETS_FROM_DRAFT_ONLY enabled; generating per draft item"
                if force_draft_mode
                else "BEST_OF_N enabled; generating per draft item with candidate selection"
            )
            self._log(
                f"STEP5_BULLETS_{section.upper()}",
                mode_msg,
                self.COLOR_WARN,
            )
            raw = ""
            items = []
            for it in summaries:
                title = str(it.get("title", "")).strip()
                draft = str(it.get("draft", "")).strip()
                items.append(
                    self._generate_item_from_draft(
                        section=section,
                        title=title,
                        draft=draft,
                        skill_memory=skill_memory,
                        original_lines=original_lines,
                    )
                )
        else:
            prompt = (
                f"You are rewriting resume {section}.\n"
                "Use these inputs:\n"
                f"- Skill memory: {json.dumps(skill_memory, ensure_ascii=False)}\n"
                f"- Original bullets: {json.dumps(original_lines, ensure_ascii=False)}\n"
                f"- Draft items: {json.dumps(summaries, ensure_ascii=False)}\n\n"
                "Return strict JSON only:\n"
                "{\"items\":[{\"title\":\"...\",\"draft\":\"...\",\"bullets\":[\"...\",\"...\"]}]}\n"
                "Rules:\n"
                "1) Do not invent facts.\n"
                "2) Bullets should reflect STAR style (action, context, result when possible).\n"
                "3) Emphasize concrete usage of listed skills where truthful.\n"
            )

            raw = self.llm.generate_json(prompt)
            data = self._extract_json_obj(raw)
            items = data.get("items", []) if isinstance(data.get("items", []), list) else []
            if not items:
                self._log(
                    f"STEP5_BULLETS_{section.upper()}",
                    "first LLM response has no parseable items; raw response below",
                    self.COLOR_WARN,
                )
                print(
                    f"{self.COLOR_WARN}[STEP5_RAW_{section.upper()}]{self.COLOR_RESET}\n"
                    f"{self._clip_text(raw)}",
                    flush=True,
                )

        parsed_items: List[Dict[str, object]] = []
        repair_raw = ""
        revised_count = 0
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            draft = str(item.get("draft", "")).strip()
            candidate_selection = item.get("candidate_selection", None)
            bullets = item.get("bullets", []) if isinstance(item.get("bullets", []), list) else []
            clean_bullets = [str(b).strip() for b in bullets if str(b).strip()]
            if not title and idx < len(summaries):
                title = summaries[idx].get("title", "")
            if not draft and idx < len(summaries):
                draft = summaries[idx].get("draft", "")

            if not clean_bullets and (title or draft):
                self._log(
                    f"STEP5_BULLETS_{section.upper()}",
                    f"item[{idx}] bullets empty; generating from draft fallback",
                    self.COLOR_WARN,
                )
                generated = self._generate_item_from_draft(
                    section=section,
                    title=title,
                    draft=draft,
                    skill_memory=skill_memory,
                    original_lines=original_lines,
                )
                title = str(generated.get("title", title)).strip()
                draft = str(generated.get("draft", draft)).strip()
                if isinstance(generated.get("candidate_selection", None), dict):
                    candidate_selection = generated.get("candidate_selection")
                clean_bullets = [
                    str(b).strip()
                    for b in generated.get("bullets", [])
                    if str(b).strip()
                ]

            final_bullets, bullet_reviews, revised_inc = self._build_bullet_reviews(
                section=section,
                title=title,
                draft=draft,
                bullets=clean_bullets,
                skill_memory=skill_memory,
                original_lines=original_lines,
            )
            revised_count += revised_inc
            payload = self._build_item_payload(
                section=section,
                title=title,
                draft=draft,
                final_bullets=final_bullets,
                bullet_reviews=bullet_reviews,
                candidate_selection=candidate_selection if isinstance(candidate_selection, dict) else None,
                original_lines=original_lines,
            )
            if isinstance(candidate_selection, dict) and candidate_selection:
                selected = candidate_selection.get("selected_index", -1)
                scores = candidate_selection.get("scores", [])
                top = scores[0].get("total", 0) if isinstance(scores, list) and scores else 0
                self._log(
                    f"STEP5_BULLETS_{section.upper()}",
                    f"item[{idx}] candidate selected={selected} score={top}",
                    self.COLOR_DATA,
                )
            parsed_items.append(payload)

        if not parsed_items and not use_per_item_generation:
            repair_content = self._prepare_repair_content(raw, limit=1200)
            if repair_content:
                # LLM repair pass: force target schema from first raw response.
                repair_prompt = (
                    "Convert the following content into strict JSON:\n"
                    "{\"items\":[{\"title\":\"...\",\"draft\":\"...\",\"bullets\":[\"...\"]}]}\n"
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
                if not repair_items:
                    self._log(
                        f"STEP5_BULLETS_{section.upper()}",
                        "repair response still has no parseable items; repair raw below",
                        self.COLOR_WARN,
                    )
                    print(
                        f"{self.COLOR_WARN}[STEP5_REPAIR_RAW_{section.upper()}]{self.COLOR_RESET}\n"
                        f"{self._clip_text(repair_raw)}",
                        flush=True,
                    )
                for idx, item in enumerate(repair_items):
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get("title", "")).strip()
                    draft = str(item.get("draft", "")).strip()
                    candidate_selection = item.get("candidate_selection", None)
                    bullets = (
                        item.get("bullets", [])
                        if isinstance(item.get("bullets", []), list)
                        else []
                    )
                    clean_bullets = [str(b).strip() for b in bullets if str(b).strip()]
                    if not title and idx < len(summaries):
                        title = summaries[idx].get("title", "")
                    if not draft and idx < len(summaries):
                        draft = summaries[idx].get("draft", "")

                    if not clean_bullets and (title or draft):
                        self._log(
                            f"STEP5_BULLETS_{section.upper()}",
                            f"repair item[{idx}] bullets empty; generating from draft fallback",
                            self.COLOR_WARN,
                        )
                        generated = self._generate_item_from_draft(
                            section=section,
                            title=title,
                            draft=draft,
                            skill_memory=skill_memory,
                            original_lines=original_lines,
                        )
                        title = str(generated.get("title", title)).strip()
                        draft = str(generated.get("draft", draft)).strip()
                        if isinstance(generated.get("candidate_selection", None), dict):
                            candidate_selection = generated.get("candidate_selection")
                        clean_bullets = [
                            str(b).strip()
                            for b in generated.get("bullets", [])
                            if str(b).strip()
                        ]

                    final_bullets, bullet_reviews, revised_inc = self._build_bullet_reviews(
                        section=section,
                        title=title,
                        draft=draft,
                        bullets=clean_bullets,
                        skill_memory=skill_memory,
                        original_lines=original_lines,
                    )
                    revised_count += revised_inc
                    payload = self._build_item_payload(
                        section=section,
                        title=title,
                        draft=draft,
                        final_bullets=final_bullets,
                        bullet_reviews=bullet_reviews,
                        candidate_selection=candidate_selection if isinstance(candidate_selection, dict) else None,
                        original_lines=original_lines,
                    )
                    parsed_items.append(payload)
            else:
                self._log(
                    f"STEP5_BULLETS_{section.upper()}",
                    "skip repair prompt due noisy/empty raw output",
                    self.COLOR_WARN,
                )

        if not parsed_items:
            self._log(
                f"STEP5_BULLETS_{section.upper()}",
                "LLM returned no bullet items; trying per-summary fallback generation",
                self.COLOR_ERR,
            )
            if raw.strip():
                print(
                    f"{self.COLOR_ERR}[STEP5_FINAL_RAW_{section.upper()}]{self.COLOR_RESET}\n"
                    f"{self._clip_text(raw)}",
                    flush=True,
                )
            if repair_raw.strip():
                print(
                    f"{self.COLOR_ERR}[STEP5_FINAL_REPAIR_RAW_{section.upper()}]{self.COLOR_RESET}\n"
                    f"{self._clip_text(repair_raw)}",
                    flush=True,
                )
            generated_items: List[Dict[str, object]] = []
            for idx, it in enumerate(summaries):
                title = str(it.get("title", "")).strip()
                draft = str(it.get("draft", "")).strip()
                self._log(
                    f"STEP5_BULLETS_{section.upper()}",
                    f"summary fallback item[{idx}] generating title+draft+bullets",
                    self.COLOR_WARN,
                )
                generated = self._generate_item_from_draft(
                    section=section,
                    title=title,
                    draft=draft,
                    skill_memory=skill_memory,
                    original_lines=original_lines,
                )
                title = str(generated.get("title", title)).strip()
                draft = str(generated.get("draft", draft)).strip()
                clean_bullets = [
                    str(b).strip() for b in generated.get("bullets", []) if str(b).strip()
                ]
                final_bullets, bullet_reviews, revised_inc = self._build_bullet_reviews(
                    section=section,
                    title=title,
                    draft=draft,
                    bullets=clean_bullets,
                    skill_memory=skill_memory,
                    original_lines=original_lines,
                )
                revised_count += revised_inc
                payload = self._build_item_payload(
                    section=section,
                    title=title,
                    draft=draft,
                    final_bullets=final_bullets,
                    bullet_reviews=bullet_reviews,
                    candidate_selection=generated.get("candidate_selection")
                    if isinstance(generated.get("candidate_selection", None), dict)
                    else None,
                    original_lines=original_lines,
                )
                generated_items.append(payload)
            parsed_items = generated_items or [
                {
                    "title": it.get("title", ""),
                    "draft": it.get("draft", ""),
                    "bullets": [],
                    "bullet_reviews": [],
                    "evidence_summary": {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "pass_ratio": 1.0,
                        "avg_support_score": 0.0,
                        "avg_consistency_score": 0.0,
                    },
                    "evidence_reports": [],
                }
                for it in summaries
            ]

        self.state.section_bullets[section] = parsed_items
        star_total = 0
        star_pass = 0
        evidence_total = 0
        evidence_pass = 0
        for it in parsed_items:
            reports = it.get("bullet_reviews", []) or it.get("bullet_star_reports", [])
            for sr in reports:
                star_total += 1
                if isinstance(sr, dict):
                    if isinstance(sr.get("star_revised"), dict) and sr["star_revised"].get("passed"):
                        star_pass += 1
                    elif isinstance(sr.get("star_original"), dict) and sr["star_original"].get("passed"):
                        star_pass += 1
            evidence_summary = it.get("evidence_summary", {})
            if isinstance(evidence_summary, dict):
                try:
                    evidence_total += int(evidence_summary.get("total", 0))
                    evidence_pass += int(evidence_summary.get("passed", 0))
                except Exception:
                    pass

        self._log(
            f"STEP5_BULLETS_{section.upper()}",
            (
                f"items={len(parsed_items)} revised={revised_count} "
                f"star_pass={star_pass}/{star_total} "
                f"evidence_pass={evidence_pass}/{evidence_total}"
            ),
            self.COLOR_OK,
        )
        return json.dumps({"section": section, "items": parsed_items}, ensure_ascii=False, indent=2)

    def build_experience_bullets(self, _: str) -> str:
        return self.build_section_bullets("experience")

    def build_projects_bullets(self, _: str) -> str:
        return self.build_section_bullets("projects")

    def compose_section_json(self, section_name: str) -> str:
        section = (section_name or "").strip().lower()
        if section not in {"experience", "projects"}:
            return '{"error":"section must be experience or projects"}'

        items = self.state.section_bullets.get(section, [])
        if not items:
            self.build_section_bullets(section)
            items = self.state.section_bullets.get(section, [])

        payload = {
            "section": section,
            "items": items,
        }
        self.state.final_section_json[section] = payload
        self.state.rewritten_sections[section] = json.dumps(payload, ensure_ascii=False, indent=2)

        self._log(f"STEP6_COMPOSE_{section.upper()}", "json composed", self.COLOR_OK)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def compose_experience_json(self, _: str) -> str:
        return self.compose_section_json("experience")

    def compose_projects_json(self, _: str) -> str:
        return self.compose_section_json("projects")

    def get_evidence_report(self, section_name: str) -> str:
        section = (section_name or "").strip().lower()
        if section not in {"experience", "projects"}:
            return '{"error":"section must be experience or projects"}'

        items = self.state.section_bullets.get(section, [])
        if not items:
            self.build_section_bullets(section)
            items = self.state.section_bullets.get(section, [])

        report_items: List[Dict[str, object]] = []
        total = 0
        passed = 0
        for idx, it in enumerate(items):
            es = it.get("evidence_summary", {})
            er = []
            if isinstance(it.get("evidence_reports", []), list):
                er = it.get("evidence_reports", [])
            else:
                # New schema: evidence is embedded in bullet_reviews[*].evidence
                bsr = it.get("bullet_reviews", []) or it.get("bullet_star_reports", [])
                if isinstance(bsr, list):
                    for row in bsr:
                        if not isinstance(row, dict):
                            continue
                        ev = row.get("evidence", {})
                        if isinstance(ev, dict) and ev:
                            er.append(ev)
            if isinstance(es, dict):
                try:
                    total += int(es.get("total", 0))
                    passed += int(es.get("passed", 0))
                except Exception:
                    pass
            report_items.append(
                {
                    "index": idx,
                    "title": it.get("title", ""),
                    "evidence_summary": es if isinstance(es, dict) else {},
                    "evidence_reports": er if isinstance(er, list) else [],
                }
            )

        payload = {
            "section": section,
            "overall": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_ratio": round((passed / total), 4) if total > 0 else 1.0,
            },
            "items": report_items,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
