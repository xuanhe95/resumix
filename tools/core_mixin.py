from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from evidence_critic import EvidenceCritic
from memory import PersistentMemoryStore
from resume_io import ResumeState


class CoreToolsMixin:
    COLOR_RESET = "\033[0m"
    COLOR_STAGE = "\033[96m"  # cyan
    COLOR_OK = "\033[92m"  # green
    COLOR_WARN = "\033[93m"  # yellow
    COLOR_ERR = "\033[91m"  # red
    COLOR_DATA = "\033[94m"  # blue

    DEFAULT_TECH_STACK = [
        "Python",
        "Java",
        "Golang",
        "Go",
        "C++",
        "C",
        "JavaScript",
        "TypeScript",
        "SQL",
        "Spring Boot",
        "Spring Cloud",
        "Django",
        "Flask",
        "FastAPI",
        "Redis",
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "Elasticsearch",
        "Kafka",
        "RabbitMQ",
        "Docker",
        "Kubernetes",
        "AWS",
        "GCP",
        "Azure",
        "Prometheus",
        "Grafana",
        "Ray",
        "LangChain",
        "LangGraph",
        "Microservices",
        "REST",
        "gRPC",
        "Terraform",
        "Nginx",
        "React",
        "Node.js",
        "PyTorch",
        "TensorFlow",
        "Spark",
        "Hadoop",
        "Airflow",
        "Git",
        "Linux",
        "Bash",
        "CI/CD",
    ]

    def __init__(self, state: ResumeState, llm):
        self.state = state
        self.llm = llm
        self.tech_stack_set = self._load_tech_stack_set()
        self.evidence_critic = EvidenceCritic()
        base_dir = os.path.dirname(os.path.dirname(__file__))
        default_memory_path = os.path.join(base_dir, "memory", "user_memory.json")
        memory_path = os.getenv("USER_MEMORY_FILE", default_memory_path).strip() or default_memory_path
        memory_user_id = os.getenv("USER_MEMORY_USER_ID", "default").strip() or "default"
        self.memory_store = PersistentMemoryStore(file_path=memory_path, user_id=memory_user_id)
        self.state.persistent_memory = self.memory_store.get_profile()
        self.state.memory_file = self.memory_store.file_path
        self._log(
            "MEMORY",
            f"loaded user profile from {self.state.memory_file}",
            self.COLOR_DATA,
        )

    def _log(self, stage: str, message: str, color: str = COLOR_STAGE) -> None:
        print(f"{color}[{stage}]{self.COLOR_RESET} {message}", flush=True)

    @staticmethod
    def _clip_text(text: str, limit: int = 2200) -> str:
        s = (text or "").strip()
        if len(s) <= limit:
            return s
        return s[:limit] + "...(truncated)"

    @staticmethod
    def _prepare_repair_content(raw: str, limit: int = 1200) -> str:
        """
        Avoid feeding very noisy/repetitive model output back into repair prompt.
        """
        s = (raw or "").strip()
        if not s:
            return ""
        words = re.findall(r"\w+", s.lower())
        if len(words) >= 120:
            uniq_ratio = len(set(words)) / max(len(words), 1)
            # Very low unique ratio usually means repetitive degenerate output.
            if uniq_ratio < 0.22:
                return ""
        if len(s) > limit:
            return s[:limit] + "...(truncated)"
        return s

    @staticmethod
    def _extract_json_obj(raw: str) -> Dict:
        s = (raw or "").strip()
        if not s:
            return {}
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _dedupe(items: List[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for x in items:
            v = str(x).strip()
            if not v or v in seen:
                continue
            seen.add(v)
            out.append(v)
        return out

    @staticmethod
    def _normalize_stack_key(term: str) -> str:
        s = re.sub(r"[^a-z0-9\+]+", "", (term or "").lower())
        aliases = {
            "golang": "go",
            "go": "go",
            "javascript": "js",
            "typescript": "ts",
            "postgres": "postgresql",
            "k8s": "kubernetes",
            "grpc": "grpc",
            "rest": "rest",
            "nodejs": "nodejs",
            "node": "nodejs",
            "cicd": "cicd",
        }
        return aliases.get(s, s)

    @staticmethod
    def _term_in_text(term: str, text: str) -> bool:
        k = (term or "").strip().lower()
        t = (text or "").lower()
        if not k or not t:
            return False
        # Use boundary-like pattern to avoid partial collisions.
        pattern = r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"
        return re.search(pattern, t) is not None

    def _load_tech_stack_set(self) -> List[str]:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        default_path = os.path.join(base_dir, "tech_stack_set.txt")
        path = os.getenv("TECH_STACK_SET_FILE", default_path).strip() or default_path

        items: List[str] = []
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        items.append(s)
        except Exception:
            items = []

        if not items:
            items = list(self.DEFAULT_TECH_STACK)

        items = self._dedupe(items)
        items.sort(key=len, reverse=True)
        self._log("TECH_STACK_SET", f"loaded={len(items)} source={path}", self.COLOR_DATA)
        return items

    def _memory_prompt_block(self) -> str:
        profile = self.state.persistent_memory if isinstance(self.state.persistent_memory, dict) else {}
        if not profile:
            return ""
        subset = {
            "target_roles": profile.get("target_roles", []),
            "tone": profile.get("tone", "concise"),
            "must_keep_facts": profile.get("must_keep_facts", []),
            "forbidden_patterns": profile.get("forbidden_patterns", []),
            "preferred_skills": profile.get("preferred_skills", []),
            "section_policies": profile.get("section_policies", {}),
        }
        return "USER_PERSISTENT_MEMORY:\n" + json.dumps(subset, ensure_ascii=False)

    def _reload_memory_profile(self) -> None:
        self.state.persistent_memory = self.memory_store.get_profile()
        self.state.memory_file = self.memory_store.file_path

    def get_persistent_memory(self, _: str) -> str:
        self._reload_memory_profile()
        return json.dumps(
            {
                "memory_file": self.state.memory_file,
                "profile": self.state.persistent_memory,
            },
            ensure_ascii=False,
            indent=2,
        )

    def update_persistent_memory(self, patch_or_feedback: str) -> str:
        raw = (patch_or_feedback or "").strip()
        if not raw:
            return '{"error":"input cannot be empty"}'

        mode = "feedback"
        if raw.startswith("{") and raw.endswith("}"):
            try:
                patch = json.loads(raw)
                if isinstance(patch, dict):
                    if isinstance(patch.get("profile", None), dict):
                        self.memory_store.set_profile(patch.get("profile", {}))
                    else:
                        self.memory_store.set_profile(patch)
                    mode = "patch"
                else:
                    self.memory_store.update_from_feedback(raw)
            except Exception:
                self.memory_store.update_from_feedback(raw)
        else:
            self.memory_store.update_from_feedback(raw)

        self._reload_memory_profile()
        self._log("MEMORY", f"updated via {mode}", self.COLOR_OK)
        return json.dumps(
            {
                "updated_via": mode,
                "memory_file": self.state.memory_file,
                "profile": self.state.persistent_memory,
            },
            ensure_ascii=False,
            indent=2,
        )

    def clear_persistent_memory(self, _: str) -> str:
        profile = self.memory_store.clear_profile()
        self.state.persistent_memory = profile
        self.state.memory_file = self.memory_store.file_path
        self._log("MEMORY", "cleared to defaults", self.COLOR_WARN)
        return json.dumps(
            {
                "memory_file": self.state.memory_file,
                "profile": profile,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _normalize_skills_from_candidates(self, candidates: List[str]) -> List[str]:
        canonical_map: Dict[str, str] = {}
        for term in self.tech_stack_set:
            canonical_map[self._normalize_stack_key(term)] = term

        matched: List[str] = []
        for raw in candidates:
            c = str(raw).strip()
            if not c:
                continue

            # exact normalized match first
            nk = self._normalize_stack_key(c)
            if nk in canonical_map:
                matched.append(canonical_map[nk])

            # then phrase scanning
            for term in self.tech_stack_set:
                if self._term_in_text(term, c):
                    matched.append(term)

        return self._dedupe(matched)

    def set_direction(self, direction: str) -> str:
        d = (direction or "").strip()
        if not d:
            return "Direction cannot be empty."
        self.state.target_direction = d
        auto_learn = os.getenv("MEMORY_AUTO_LEARN_DIRECTION", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if auto_learn:
            self.memory_store.set_profile({"target_roles": [d]})
            self._reload_memory_profile()
        self._log("DIRECTION", f"target={d}", self.COLOR_OK)
        return f"Target direction set to: {d}"
