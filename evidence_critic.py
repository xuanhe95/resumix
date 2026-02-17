from __future__ import annotations

import os
import re
import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

try:
    from rapidfuzz import fuzz as rf_fuzz
except Exception:
    rf_fuzz = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import faiss
except Exception:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[\u2013\u2014]", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9\+\#\./%-]+", _normalize_text(s))


def _token_jaccard(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _similarity(a: str, b: str) -> float:
    aa = _normalize_text(a)
    bb = _normalize_text(b)
    if not aa or not bb:
        return 0.0
    if rf_fuzz is not None:
        return float(rf_fuzz.token_set_ratio(aa, bb)) / 100.0
    return SequenceMatcher(None, aa, bb).ratio()


def _extract_numeric_tokens(text: str) -> List[str]:
    """
    Extract numeric-like tokens to detect fabricated metrics.
    """
    raw = re.findall(
        r"(?:[<>]=?)?\d+(?:\.\d+)?(?:%|x|×|k\+?|m\+?|b\+?|s|ms|min|h)?",
        (text or "").lower(),
    )
    out: List[str] = []
    seen = set()
    for x in raw:
        n = x.strip()
        if not n:
            continue
        if n.endswith(".0"):
            n = n[:-2]
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _contains_term(term: str, text: str) -> bool:
    t = _normalize_text(term)
    x = _normalize_text(text)
    if not t or not x:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
    return re.search(pattern, x) is not None


@dataclass
class EvidenceCriticConfig:
    top_k: int = 3
    min_support_score: float = 0.42
    min_consistency_score: float = 0.45
    strict_numeric: bool = True
    strict_skill: bool = False
    use_faiss: bool = True
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls) -> "EvidenceCriticConfig":
        def _env_float(name: str, default: float) -> float:
            v = os.getenv(name, "").strip()
            if not v:
                return default
            try:
                return float(v)
            except Exception:
                return default

        def _env_int(name: str, default: int) -> int:
            v = os.getenv(name, "").strip()
            if not v:
                return default
            try:
                return int(v)
            except Exception:
                return default

        def _env_bool(name: str, default: bool) -> bool:
            v = os.getenv(name, "").strip().lower()
            if not v:
                return default
            return v in {"1", "true", "yes", "on"}

        return cls(
            top_k=max(1, min(8, _env_int("EVIDENCE_TOP_K", 3))),
            min_support_score=_env_float("EVIDENCE_MIN_SUPPORT_SCORE", 0.42),
            min_consistency_score=_env_float("EVIDENCE_MIN_CONSISTENCY_SCORE", 0.45),
            strict_numeric=_env_bool("EVIDENCE_STRICT_NUMERIC", True),
            strict_skill=_env_bool("EVIDENCE_STRICT_SKILL", False),
            use_faiss=_env_bool("EVIDENCE_USE_FAISS", True),
            embed_model=os.getenv("EVIDENCE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
            or "sentence-transformers/all-MiniLM-L6-v2",
        )


class EvidenceCritic:
    """
    Evidence-based critic:
    - retrieve top-k source lines for each bullet
    - check support similarity + numeric/skill consistency
    """

    def __init__(self, config: Optional[EvidenceCriticConfig] = None):
        self.cfg = config or EvidenceCriticConfig.from_env()
        self._encoder: Any = None
        self._index_cache: Dict[str, Dict[str, Any]] = {}
        self.debug = os.getenv("VECTOR_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.local_only = os.getenv("EMBED_LOCAL_ONLY", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._faiss_ready = bool(
            self.cfg.use_faiss and np is not None and faiss is not None and SentenceTransformer is not None
        )

    def _get_encoder(self):
        if not self._faiss_ready:
            return None
        if self._encoder is None:
            try:
                if self.local_only:
                    self._encoder = SentenceTransformer(self.cfg.embed_model, local_files_only=True)
                else:
                    self._encoder = SentenceTransformer(self.cfg.embed_model)
            except TypeError:
                if self.local_only:
                    return None
                self._encoder = SentenceTransformer(self.cfg.embed_model)
            except Exception:
                return None
        return self._encoder

    @staticmethod
    def _normalize_vecs(arr):
        if np is None:
            return arr
        if arr is None:
            return arr
        if getattr(arr, "ndim", 0) == 1:
            arr = arr.reshape(1, -1)
        arr = arr.astype("float32")
        if faiss is not None:
            faiss.normalize_L2(arr)
        else:
            denom = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
            arr = arr / denom
        return arr

    def _build_index(self, section: str, source_lines: List[str]) -> Dict[str, Any]:
        items: List[Dict[str, object]] = []
        for i, line in enumerate(source_lines):
            text = str(line).strip()
            if not text:
                continue
            items.append(
                {
                    "id": f"{section}_{i+1}",
                    "text": text,
                }
            )
        out: Dict[str, Any] = {"items": items}
        if not self._faiss_ready or not items:
            return out

        key_raw = section + "\n" + "\n".join(str(x.get("text", "")) for x in items)
        key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()
        cached = self._index_cache.get(key)
        if cached is not None:
            return cached

        encoder = self._get_encoder()
        if encoder is None or np is None or faiss is None:
            if self.debug:
                print(
                    f"[EVIDENCE][FAISS] encoder unavailable (model={self.cfg.embed_model}, local_only={self.local_only}), fallback lexical",
                    flush=True,
                )
            return out

        try:
            if self.debug:
                print(
                    f"[EVIDENCE][FAISS] building index section={section} lines={len(items)} model={self.cfg.embed_model}",
                    flush=True,
                )
            texts = [str(x.get("text", "")) for x in items]
            vecs = encoder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            arr = np.asarray(vecs, dtype="float32")
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            arr = self._normalize_vecs(arr)
            dim = int(arr.shape[1])
            faiss_index = faiss.IndexFlatIP(dim)
            faiss_index.add(arr)
            payload = {
                "items": items,
                "faiss_index": faiss_index,
                "faiss_ready": True,
                "key": key,
            }
            self._index_cache[key] = payload
            if self.debug:
                print("[EVIDENCE][FAISS] index ready", flush=True)
            return payload
        except Exception as e:
            if self.debug:
                print(f"[EVIDENCE][FAISS] build failed: {e}; fallback lexical", flush=True)
            return out

    def _retrieve_evidence_lexical(self, bullet: str, items: List[Dict[str, Any]]) -> List[Dict[str, object]]:
        scored: List[Dict[str, object]] = []
        for item in items:
            text = str(item.get("text", ""))
            sim = _similarity(bullet, text)
            jac = _token_jaccard(bullet, text)
            score = (sim * 0.75) + (jac * 0.25)
            scored.append(
                {
                    "id": item.get("id", ""),
                    "text": text,
                    "score": round(score, 4),
                    "retriever": "lexical",
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: self.cfg.top_k]

    def _retrieve_evidence_faiss(self, bullet: str, payload: Dict[str, Any]) -> List[Dict[str, object]]:
        if not self._faiss_ready or np is None or faiss is None:
            return []
        items = payload.get("items", [])
        index = payload.get("faiss_index", None)
        if not isinstance(items, list) or index is None:
            return []
        encoder = self._get_encoder()
        if encoder is None:
            return []
        try:
            q = encoder.encode([bullet], convert_to_numpy=True, show_progress_bar=False)
            q_arr = np.asarray(q, dtype="float32")
            if q_arr.ndim == 1:
                q_arr = q_arr.reshape(1, -1)
            q_arr = self._normalize_vecs(q_arr)
            k = min(self.cfg.top_k, max(len(items), 1))
            scores, idxs = index.search(q_arr, k)
            out: List[Dict[str, object]] = []
            for rank, ridx in enumerate(idxs[0]):
                j = int(ridx)
                if j < 0 or j >= len(items):
                    continue
                raw_score = float(scores[0][rank])
                # cosine/IP from normalized vectors -> [-1, 1], map to [0, 1]
                score = max(0.0, min(1.0, (raw_score + 1.0) / 2.0))
                item = items[j]
                out.append(
                    {
                        "id": item.get("id", ""),
                        "text": str(item.get("text", "")),
                        "score": round(score, 4),
                        "retriever": "faiss",
                    }
                )
            return out
        except Exception:
            return []

    def _retrieve_evidence(self, bullet: str, payload: Dict[str, Any]) -> List[Dict[str, object]]:
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        if self._faiss_ready:
            via_faiss = self._retrieve_evidence_faiss(bullet, payload)
            if via_faiss:
                return via_faiss
        return self._retrieve_evidence_lexical(bullet, items)

    def _skill_consistency(
        self,
        bullet: str,
        evidence_text: str,
        skill_facts: List[str],
        source_lines: List[str],
    ) -> Dict[str, object]:
        known_pool = [str(x).strip() for x in (skill_facts + source_lines) if str(x).strip()]
        known_skill_hits: List[str] = []
        for s in skill_facts:
            ss = str(s).strip()
            if ss and _contains_term(ss, bullet):
                known_skill_hits.append(ss)

        unsupported: List[str] = []
        # Optional strict check: terms that look like tech words but not in known pool.
        if self.cfg.strict_skill:
            tokens = _tokenize(bullet)
            for tk in tokens:
                if len(tk) < 3:
                    continue
                if tk.isdigit():
                    continue
                if any(_contains_term(tk, src) for src in known_pool):
                    continue
                # Skip high-frequency generic words.
                if tk in {
                    "system",
                    "service",
                    "services",
                    "project",
                    "projects",
                    "platform",
                    "api",
                    "apis",
                    "data",
                    "model",
                    "models",
                    "team",
                }:
                    continue
                unsupported.append(tk)

        return {
            "matched_skills": sorted(set(known_skill_hits)),
            "unsupported_skill_terms": sorted(set(unsupported)),
            "skill_consistent": len(unsupported) == 0,
            "evidence_skill_overlap": sum(1 for s in known_skill_hits if _contains_term(s, evidence_text)),
        }

    def evaluate_bullet(
        self,
        *,
        section: str,
        bullet: str,
        source_lines: List[str],
        skill_facts: List[str],
    ) -> Dict[str, object]:
        text = (bullet or "").strip()
        index = self._build_index(section, source_lines)
        refs = self._retrieve_evidence(text, index)
        top_score = float(refs[0]["score"]) if refs else 0.0

        evidence_join = "\n".join(str(x.get("text", "")) for x in refs)
        overlap = _token_jaccard(text, evidence_join)

        bullet_nums = _extract_numeric_tokens(text)
        evidence_nums = _extract_numeric_tokens(evidence_join)
        missing_nums = [n for n in bullet_nums if n not in evidence_nums]
        numeric_consistent = len(missing_nums) == 0 or (not self.cfg.strict_numeric)

        skill_report = self._skill_consistency(text, evidence_join, skill_facts, source_lines)
        skill_consistent = bool(skill_report.get("skill_consistent", True))

        consistency_score = (top_score * 0.7) + (overlap * 0.3)
        if self.cfg.strict_numeric and missing_nums:
            consistency_score *= 0.55
        if self.cfg.strict_skill and not skill_consistent:
            consistency_score *= 0.65

        passed = (
            top_score >= self.cfg.min_support_score
            and consistency_score >= self.cfg.min_consistency_score
            and numeric_consistent
            and skill_consistent
        )

        reason_parts: List[str] = []
        reason_parts.append(f"support={round(top_score, 4)}")
        reason_parts.append(f"consistency={round(consistency_score, 4)}")
        if missing_nums:
            reason_parts.append(f"missing_numeric={missing_nums}")
        unsupported = skill_report.get("unsupported_skill_terms", [])
        if unsupported:
            reason_parts.append(f"unsupported_skill_terms={unsupported}")

        return {
            "bullet": text,
            "evidence_refs": refs,
            "support_score": round(top_score, 4),
            "token_overlap": round(overlap, 4),
            "consistency_score": round(consistency_score, 4),
            "numeric_consistent": numeric_consistent,
            "missing_numeric_tokens": missing_nums,
            "matched_skills": skill_report.get("matched_skills", []),
            "unsupported_skill_terms": unsupported,
            "passed": passed,
            "reason": "; ".join(reason_parts),
        }

    def evaluate_item(
        self,
        *,
        section: str,
        title: str,
        draft: str,
        bullets: List[str],
        source_lines: List[str],
        skill_facts: List[str],
    ) -> Dict[str, object]:
        reports = [
            self.evaluate_bullet(
                section=section,
                bullet=str(b),
                source_lines=source_lines,
                skill_facts=skill_facts,
            )
            for b in bullets
            if str(b).strip()
        ]
        passed = sum(1 for r in reports if bool(r.get("passed", False)))
        total = len(reports)
        avg_support = round(
            sum(float(r.get("support_score", 0.0)) for r in reports) / max(total, 1),
            4,
        )
        avg_consistency = round(
            sum(float(r.get("consistency_score", 0.0)) for r in reports) / max(total, 1),
            4,
        )
        summary = {
            "title": title,
            "draft": draft,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_ratio": round((passed / total), 4) if total > 0 else 1.0,
            "avg_support_score": avg_support,
            "avg_consistency_score": avg_consistency,
            "thresholds": {
                "min_support_score": self.cfg.min_support_score,
                "min_consistency_score": self.cfg.min_consistency_score,
                "strict_numeric": self.cfg.strict_numeric,
                "strict_skill": self.cfg.strict_skill,
                "use_faiss": self._faiss_ready,
                "embed_model": self.cfg.embed_model if self._faiss_ready else "",
            },
        }
        return {
            "summary": summary,
            "bullet_reports": reports,
        }
