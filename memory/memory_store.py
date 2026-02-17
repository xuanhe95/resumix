from __future__ import annotations

import copy
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dedupe_list(items: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for x in items:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def _deep_merge(base: Any, patch: Any) -> Any:
    if isinstance(base, dict) and isinstance(patch, dict):
        out = dict(base)
        for k, v in patch.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out
    if isinstance(base, list) and isinstance(patch, list):
        return _dedupe_list(list(base) + list(patch))
    return copy.deepcopy(patch)


class PersistentMemoryStore:
    def __init__(self, file_path: str, user_id: str = "default"):
        self.file_path = os.path.abspath(os.path.expanduser(file_path))
        self.user_id = user_id

    def _default_doc(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "user_id": self.user_id,
            "profile": {
                "target_roles": [],
                "tone": "concise",
                "must_keep_facts": [],
                "forbidden_patterns": [],
                "preferred_skills": [],
                "section_policies": {
                    "personal_info": "passthrough",
                    "education": "passthrough",
                    "skills": "passthrough",
                    "experience": "rewrite",
                    "projects": "rewrite",
                },
            },
            "stats": {
                "memory_updates": 0,
                "last_feedbacks": [],
            },
            "updated_at": "",
        }

    def _ensure_parent(self) -> None:
        parent = os.path.dirname(self.file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def load_doc(self) -> Dict[str, Any]:
        self._ensure_parent()
        if not os.path.exists(self.file_path):
            doc = self._default_doc()
            self.save_doc(doc)
            return doc

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("memory doc is not object")
            doc = _deep_merge(self._default_doc(), data)
            return doc
        except Exception:
            # Reset corrupted file with default schema to keep pipeline robust.
            doc = self._default_doc()
            self.save_doc(doc)
            return doc

    def save_doc(self, doc: Dict[str, Any]) -> None:
        self._ensure_parent()
        payload = _deep_merge(self._default_doc(), doc)
        payload["updated_at"] = _now_iso()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def get_profile(self) -> Dict[str, Any]:
        doc = self.load_doc()
        profile = doc.get("profile", {})
        return profile if isinstance(profile, dict) else {}

    def set_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        doc = self.load_doc()
        doc["profile"] = _deep_merge(doc.get("profile", {}), profile if isinstance(profile, dict) else {})
        stats = doc.get("stats", {})
        if isinstance(stats, dict):
            stats["memory_updates"] = int(stats.get("memory_updates", 0)) + 1
            doc["stats"] = stats
        self.save_doc(doc)
        return self.get_profile()

    def clear_profile(self) -> Dict[str, Any]:
        doc = self._default_doc()
        self.save_doc(doc)
        return self.get_profile()

    @staticmethod
    def _extract_list_after_keyword(text: str, keyword: str) -> List[str]:
        t = text
        idx = t.lower().find(keyword.lower())
        if idx < 0:
            return []
        chunk = t[idx + len(keyword):]
        chunk = chunk.split("\n", 1)[0]
        chunk = chunk.replace("：", ":")
        if ":" in chunk:
            chunk = chunk.split(":", 1)[1]
        parts = re.split(r"[;,，、]\s*", chunk)
        out = [p.strip().strip("\"'") for p in parts if p.strip()]
        return out

    def extract_patch_from_feedback(self, feedback: str) -> Dict[str, Any]:
        raw = (feedback or "").strip()
        if not raw:
            return {}
        lower = raw.lower()

        patch: Dict[str, Any] = {}

        section_policies: Dict[str, str] = {}
        no_change_patterns: List[Tuple[str, str]] = [
            ("personal info", "personal_info"),
            ("personal_information", "personal_info"),
            ("education", "education"),
            ("skills", "skills"),
            ("experience", "experience"),
            ("projects", "projects"),
            ("个人信息", "personal_info"),
            ("教育", "education"),
            ("技能", "skills"),
            ("经历", "experience"),
            ("项目", "projects"),
        ]
        for kw, sec in no_change_patterns:
            if (f"不要改{kw}" in lower) or (f"don't change {kw}" in lower) or (f"no rewrite {kw}" in lower):
                section_policies[sec] = "passthrough"
            if (f"重写{kw}" in lower) or (f"rewrite {kw}" in lower):
                section_policies[sec] = "rewrite"

        if section_policies:
            patch["section_policies"] = section_policies

        if ("简洁" in raw) or ("concise" in lower):
            patch["tone"] = "concise"
        elif ("详细" in raw) or ("detailed" in lower):
            patch["tone"] = "detailed"

        role_hits = re.findall(
            r"(backend engineer|frontend engineer|full[- ]?stack engineer|software engineer|data engineer|ml engineer|sre|platform engineer)",
            lower,
        )
        if role_hits:
            patch["target_roles"] = [x.strip() for x in role_hits if x.strip()]

        keep_facts = self._extract_list_after_keyword(raw, "must keep")
        keep_facts += self._extract_list_after_keyword(raw, "必须保留")
        if keep_facts:
            patch["must_keep_facts"] = keep_facts

        forbidden = self._extract_list_after_keyword(raw, "forbidden")
        forbidden += self._extract_list_after_keyword(raw, "禁用词")
        if forbidden:
            patch["forbidden_patterns"] = forbidden

        preferred = self._extract_list_after_keyword(raw, "preferred skills")
        preferred += self._extract_list_after_keyword(raw, "偏好技能")
        if preferred:
            patch["preferred_skills"] = preferred

        return patch

    def append_feedback(self, feedback: str) -> None:
        raw = (feedback or "").strip()
        if not raw:
            return
        doc = self.load_doc()
        stats = doc.get("stats", {})
        if not isinstance(stats, dict):
            stats = {}
        logs = stats.get("last_feedbacks", [])
        if not isinstance(logs, list):
            logs = []
        logs.append({"ts": _now_iso(), "text": raw})
        stats["last_feedbacks"] = logs[-20:]
        doc["stats"] = stats
        self.save_doc(doc)

    def update_from_feedback(self, feedback: str) -> Dict[str, Any]:
        patch = self.extract_patch_from_feedback(feedback)
        if patch:
            self.set_profile(patch)
        self.append_feedback(feedback)
        return self.get_profile()

