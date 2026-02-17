from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional


def _slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "profile"


class RecordExporter:
    def __init__(self, records_dir: str):
        self.records_dir = os.path.abspath(os.path.expanduser(records_dir))
        os.makedirs(self.records_dir, exist_ok=True)

    @staticmethod
    def derive_profile_name(
        *,
        memory_profile: Optional[Dict[str, Any]] = None,
        target_direction: str = "",
        fallback_user_id: str = "default",
    ) -> str:
        profile = memory_profile if isinstance(memory_profile, dict) else {}

        explicit_name = str(profile.get("profile_name", "")).strip()
        if explicit_name:
            return explicit_name

        roles = profile.get("target_roles", [])
        if isinstance(roles, list) and roles:
            first = str(roles[0]).strip()
            if first:
                return first

        if str(target_direction).strip():
            return str(target_direction).strip()

        return str(fallback_user_id or "default").strip()

    def save_final_json(
        self,
        final_payload: Dict[str, Any],
        *,
        profile_name: str,
    ) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"{_slugify(profile_name)}_{ts}.json"
        path = os.path.join(self.records_dir, fn)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)
        return path
