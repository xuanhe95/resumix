from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional


class ResumeReportPrinter:
    COLOR_RESET = "\033[0m"
    COLOR_HEADER = "\033[96m"
    # Base section colors: standard readable ANSI depth.
    COLOR_PERSONAL = "\033[35m"
    COLOR_EDU = "\033[36m"
    COLOR_SKILLS = "\033[33m"
    COLOR_EXP = "\033[32m"
    COLOR_PROJ = "\033[34m"
    COLOR_HINT = "\033[90m"
    COLOR_COMPARE = "\033[35m"
    ITALIC_ON = "\033[3m"
    ITALIC_OFF = "\033[23m"
    # Changed-token colors: muted/desaturated variants per section.
    COLOR_PERSONAL_MUTED = "\033[2;38;5;139m"  # gray-purple
    COLOR_EDU_MUTED = "\033[2;38;5;110m"  # gray-cyan
    COLOR_SKILLS_MUTED = "\033[2;38;5;179m"  # gray-yellow
    COLOR_EXP_MUTED = "\033[2;38;5;108m"  # gray-green
    COLOR_PROJ_MUTED = "\033[2;38;5;109m"  # gray-blue

    SECTION_COLOR = {
        "personal_info": COLOR_PERSONAL,
        "education": COLOR_EDU,
        "skills": COLOR_SKILLS,
        "experience": COLOR_EXP,
        "projects": COLOR_PROJ,
    }

    SECTION_LIGHT_COLOR = {
        "personal_info": COLOR_PERSONAL_MUTED,
        "education": COLOR_EDU_MUTED,
        "skills": COLOR_SKILLS_MUTED,
        "experience": COLOR_EXP_MUTED,
        "projects": COLOR_PROJ_MUTED,
    }

    @staticmethod
    def _as_items(section_obj: Any) -> List[Any]:
        if isinstance(section_obj, dict):
            items = section_obj.get("items", [])
            if isinstance(items, list):
                return items
        if isinstance(section_obj, list):
            return section_obj
        return []

    @staticmethod
    def _short(text: str, n: int = 360) -> str:
        s = (text or "").strip()
        if len(s) <= n:
            return s
        return s[: n - 3].rstrip() + "..."

    def _render_base(self, section: str, items: List[Any]) -> str:
        color = self.SECTION_COLOR.get(section, self.COLOR_RESET)
        lines = [f"{color}[{section}]{self.COLOR_RESET}"]
        if not items:
            lines.append(f"{self.COLOR_HINT}(empty){self.COLOR_RESET}")
            return "\n".join(lines)
        for x in items:
            lines.append(f"{color}- {str(x)}{self.COLOR_RESET}")
        return "\n".join(lines)

    def _render_complex(self, section: str, items: List[Any]) -> str:
        color = self.SECTION_COLOR.get(section, self.COLOR_RESET)
        lines = [f"{color}[{section}]{self.COLOR_RESET}"]
        if not items:
            lines.append(f"{self.COLOR_HINT}(empty){self.COLOR_RESET}")
            return "\n".join(lines)

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                lines.append(f"{color}{idx}. {str(item)}{self.COLOR_RESET}")
                continue
            title = str(item.get("title", "")).strip()
            draft = str(item.get("draft", "")).strip()
            bullets = item.get("bullets", [])
            if not isinstance(bullets, list):
                bullets = []
            lines.append(f"{color}{idx}. {title or '(untitled)'}{self.COLOR_RESET}")
            if draft:
                lines.append(f"{self.COLOR_HINT}   draft: {self._short(draft)}{self.COLOR_RESET}")
            if bullets:
                for b in bullets:
                    lines.append(f"{color}   - {str(b)}{self.COLOR_RESET}")
            else:
                lines.append(f"{self.COLOR_HINT}   - (no bullets){self.COLOR_RESET}")
        return "\n".join(lines)

    def _section_text(self, section: str, items: List[Any], include_draft: bool = True) -> str:
        if section in {"personal_info", "education", "skills"}:
            if not items:
                return "(empty)"
            return "\n".join(f"- {str(x)}" for x in items)

        # complex section: experience / projects
        if not items:
            return "(empty)"
        lines: List[str] = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                lines.append(f"{idx}. {str(item)}")
                continue
            title = str(item.get("title", "")).strip()
            draft = str(item.get("draft", "")).strip()
            bullets = item.get("bullets", [])
            if not isinstance(bullets, list):
                bullets = []
            lines.append(f"{idx}. {title or '(untitled)'}")
            if include_draft and draft:
                lines.append(f"   draft: {draft}")
            if bullets:
                for b in bullets:
                    lines.append(f"   - {str(b)}")
            else:
                lines.append("   - (no bullets)")
        return "\n".join(lines)

    @staticmethod
    def _norm_line(text: str) -> str:
        return " ".join((text or "").strip().lower().split())

    @staticmethod
    def _split_tokens_keep_space(line: str) -> List[str]:
        # Keep whitespace as tokens so we can reconstruct line formatting.
        return re.findall(r"\s+|[^\s]+", line or "")

    def _highlight_line_diff(
        self,
        original_line: str,
        final_line: str,
        base_color: str,
        light_color: str,
    ) -> tuple[str, bool]:
        a = self._split_tokens_keep_space(original_line)
        b = self._split_tokens_keep_space(final_line)
        seq = difflib.SequenceMatcher(
            a=[x.lower() for x in a],
            b=[x.lower() for x in b],
        )
        parts: List[str] = []
        changed = False
        for tag, _i1, _i2, j1, j2 in seq.get_opcodes():
            chunk = "".join(b[j1:j2])
            if not chunk:
                continue
            if tag == "equal":
                # Unchanged text (from original) uses muted color.
                parts.append(f"{light_color}{chunk}{self.COLOR_RESET}")
            else:
                changed = True
                # Changed text uses normal section color + italic.
                parts.append(
                    f"{base_color}{self.ITALIC_ON}{chunk}{self.ITALIC_OFF}{self.COLOR_RESET}"
                )
        return "".join(parts), changed

    def _highlight_changes(
        self,
        original_text: str,
        final_text: str,
        base_color: str,
        light_color: str,
    ) -> tuple[str, int]:
        if not final_text:
            return f"{base_color}(empty){self.COLOR_RESET}", 0

        original_lines = (original_text or "").splitlines()
        final_lines = (final_text or "").splitlines()
        seq = difflib.SequenceMatcher(
            a=[self._norm_line(x) for x in original_lines],
            b=[self._norm_line(x) for x in final_lines],
        )
        parts: List[str] = []
        changed_lines = 0
        for tag, i1, i2, j1, j2 in seq.get_opcodes():
            chunk_lines = final_lines[j1:j2]
            if not chunk_lines:
                continue
            if tag == "equal":
                for line in chunk_lines:
                    parts.append(f"{light_color}{line}{self.COLOR_RESET}")
            else:
                for idx, line in enumerate(chunk_lines):
                    orig_line = original_lines[i1 + idx] if (i1 + idx) < i2 else ""
                    rendered, changed = self._highlight_line_diff(
                        orig_line,
                        line,
                        base_color=base_color,
                        light_color=light_color,
                    )
                    parts.append(rendered)
                    if changed:
                        changed_lines += 1
        return "\n".join(parts), changed_lines

    def _render_inline_diff_base_section(
        self,
        section: str,
        original_items: List[Any],
        final_items: List[Any],
    ) -> str:
        color = self.SECTION_COLOR.get(section, self.COLOR_RESET)
        light_color = self.SECTION_LIGHT_COLOR.get(section, color)
        original_text = self._section_text(section, original_items, include_draft=True)
        final_text = self._section_text(section, final_items, include_draft=True)
        highlighted_final, changed_lines = self._highlight_changes(
            original_text,
            final_text,
            base_color=color,
            light_color=light_color,
        )

        lines = [f"{self.COLOR_COMPARE}[compare:{section}]{self.COLOR_RESET}"]
        lines.append(
            f"{self.COLOR_HINT}rewritten (original muted, changed normal+italic): {changed_lines} lines{self.COLOR_RESET}"
        )
        lines.append(highlighted_final)
        return "\n".join(lines)

    def _render_inline_diff_complex_section(
        self,
        section: str,
        original_items: List[Any],
        final_items: List[Any],
    ) -> str:
        color = self.SECTION_COLOR.get(section, self.COLOR_RESET)
        light_color = self.SECTION_LIGHT_COLOR.get(section, color)
        lines = [f"{self.COLOR_COMPARE}[compare:{section}]{self.COLOR_RESET}"]
        changed_lines = 0
        n = max(len(original_items), len(final_items))
        if n == 0:
            lines.append(f"{self.COLOR_HINT}(empty){self.COLOR_RESET}")
            return "\n".join(lines)

        for idx in range(n):
            o = original_items[idx] if idx < len(original_items) and isinstance(original_items[idx], dict) else {}
            f = final_items[idx] if idx < len(final_items) and isinstance(final_items[idx], dict) else {}

            o_title = str(o.get("title", "")).strip()
            f_title = str(f.get("title", "")).strip()
            o_title_line = f"{idx + 1}. {o_title or '(untitled)'}"
            f_title_line = f"{idx + 1}. {f_title or '(untitled)'}"
            rendered_title, changed = self._highlight_line_diff(
                o_title_line,
                f_title_line,
                base_color=color,
                light_color=light_color,
            )
            lines.append(rendered_title)
            if changed:
                changed_lines += 1

            # Draft is NOT compared. Show final draft in gray only.
            f_draft = str(f.get("draft", "")).strip()
            if f_draft:
                lines.append(f"{self.COLOR_HINT}   draft: {f_draft}{self.COLOR_RESET}")

            o_b = o.get("bullets", []) if isinstance(o.get("bullets", []), list) else []
            f_b = f.get("bullets", []) if isinstance(f.get("bullets", []), list) else []
            m = max(len(o_b), len(f_b))
            if m == 0:
                lines.append(f"{self.COLOR_HINT}   - (no bullets){self.COLOR_RESET}")
                continue
            for j in range(m):
                ob = str(o_b[j]).strip() if j < len(o_b) else ""
                fb = str(f_b[j]).strip() if j < len(f_b) else ""
                ob_line = f"   - {ob}" if ob else ""
                fb_line = f"   - {fb}" if fb else ""
                rendered_b, changed_b = self._highlight_line_diff(
                    ob_line,
                    fb_line,
                    base_color=color,
                    light_color=light_color,
                )
                if rendered_b:
                    lines.append(rendered_b)
                if changed_b:
                    changed_lines += 1

        lines.insert(
            1,
            f"{self.COLOR_HINT}rewritten (original muted, changed normal+italic, draft passthrough): {changed_lines} lines{self.COLOR_RESET}",
        )
        return "\n".join(lines)

    def render(
        self,
        final_payload: Dict[str, Any],
        record_path: str = "",
        original_payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        lines = [f"{self.COLOR_HEADER}=== Resume Report ==={self.COLOR_RESET}"]
        if record_path:
            lines.append(f"{self.COLOR_HINT}record: {record_path}{self.COLOR_RESET}")

        base_sections = ["personal_info", "education", "skills"]
        complex_sections = ["experience", "projects"]

        for sec in base_sections:
            items = self._as_items(final_payload.get(sec, {}))
            lines.append("")
            lines.append(self._render_base(sec, items))

        for sec in complex_sections:
            items = self._as_items(final_payload.get(sec, {}))
            lines.append("")
            lines.append(self._render_complex(sec, items))

        skills_to_add = final_payload.get("skills_to_add", [])
        if isinstance(skills_to_add, list):
            lines.append("")
            lines.append(f"{self.COLOR_HEADER}[skills_to_add]{self.COLOR_RESET}")
            if skills_to_add:
                for s in skills_to_add:
                    lines.append(f"{self.COLOR_SKILLS}- {str(s)}{self.COLOR_RESET}")
            else:
                lines.append(f"{self.COLOR_HINT}(none){self.COLOR_RESET}")

        if isinstance(original_payload, dict) and original_payload:
            lines.append("")
            lines.append(
                f"{self.COLOR_HEADER}=== Original + Rewritten (Inline Highlight) ==={self.COLOR_RESET}"
            )

            for sec in ["personal_info", "education", "skills", "experience", "projects"]:
                o_items = self._as_items(original_payload.get(sec, {}))
                f_items = self._as_items(final_payload.get(sec, {}))
                lines.append("")
                if sec in {"experience", "projects"}:
                    lines.append(self._render_inline_diff_complex_section(sec, o_items, f_items))
                else:
                    lines.append(self._render_inline_diff_base_section(sec, o_items, f_items))

        return "\n".join(lines)

    def print_report(
        self,
        final_payload: Dict[str, Any],
        record_path: str = "",
        original_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        print(
            self.render(
                final_payload,
                record_path=record_path,
                original_payload=original_payload,
            ),
            flush=True,
        )
