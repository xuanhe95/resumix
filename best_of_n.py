from __future__ import annotations

import os
import re
import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

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


def _contains_term(term: str, text: str) -> bool:
    t = _normalize_text(term)
    x = _normalize_text(text)
    if not t or not x:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
    return re.search(pattern, x) is not None


def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9\+\#\.]+", _normalize_text(s))


def _jaccard(a: List[str], b: List[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _best_similarity_lexical(query: str, candidates: List[str]) -> float:
    q = _normalize_text(query)
    if not q:
        return 0.0
    best = 0.0
    for c in candidates:
        cc = _normalize_text(c)
        if not cc:
            continue
        if rf_fuzz is not None:
            score = float(rf_fuzz.token_set_ratio(q, cc)) / 100.0
        else:
            score = SequenceMatcher(None, q, cc).ratio()
        if score > best:
            best = score
    return best


def _star_score(bullet: str) -> float:
    b = (bullet or "").strip()
    if not b:
        return 0.0

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
    return float(score) / 3.0


@dataclass
class CandidateScore:
    index: int
    total: float
    star: float
    faithfulness: float
    skill_alignment: float
    structure: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "index": self.index,
            "total": round(self.total, 4),
            "star": round(self.star, 4),
            "faithfulness": round(self.faithfulness, 4),
            "skill_alignment": round(self.skill_alignment, 4),
            "structure": round(self.structure, 4),
        }


class BestOfNSelector:
    """
    Deterministic ranker for candidate resume items.
    """

    _ENCODER_CACHE: Dict[str, Any] = {}
    _INDEX_CACHE: Dict[str, Dict[str, Any]] = {}

    def __init__(self, skill_memory: List[str], original_lines: List[str]):
        self.skill_memory = [str(x).strip() for x in skill_memory if str(x).strip()]
        self.original_lines = [str(x).strip() for x in original_lines if str(x).strip()]
        self._source_text = " ".join(self.original_lines)
        self._source_tokens = _tokenize(self._source_text)
        self.debug = os.getenv("VECTOR_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.use_faiss = os.getenv("BEST_OF_N_USE_FAISS", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.local_only = os.getenv("EMBED_LOCAL_ONLY", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.embed_model = (
            os.getenv("BEST_OF_N_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
            or "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._faiss_ready = bool(
            self.use_faiss and np is not None and faiss is not None and SentenceTransformer is not None
        )
        self._faiss_payload = self._build_faiss_payload()

    @classmethod
    def _get_encoder(cls, model_name: str):
        local_only = os.getenv("EMBED_LOCAL_ONLY", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if SentenceTransformer is None:
            return None
        enc = cls._ENCODER_CACHE.get(model_name)
        if enc is not None:
            return enc
        try:
            if local_only:
                enc = SentenceTransformer(model_name, local_files_only=True)
            else:
                enc = SentenceTransformer(model_name)
        except TypeError:
            # Older sentence-transformers may not support local_files_only.
            if local_only:
                return None
            enc = SentenceTransformer(model_name)
        except Exception:
            return None
        cls._ENCODER_CACHE[model_name] = enc
        return enc

    @staticmethod
    def _normalize_vecs(arr):
        if np is None:
            return arr
        arr = arr.astype("float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if faiss is not None:
            faiss.normalize_L2(arr)
        else:
            denom = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
            arr = arr / denom
        return arr

    def _build_faiss_payload(self) -> Optional[Dict[str, Any]]:
        if not self._faiss_ready or not self.original_lines:
            return None
        key_raw = self.embed_model + "\n" + "\n".join(self.original_lines)
        key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()
        cached = self._INDEX_CACHE.get(key)
        if cached is not None:
            return cached
        encoder = self._get_encoder(self.embed_model)
        if encoder is None or np is None or faiss is None:
            if self.debug:
                print(
                    f"[BEST_OF_N][FAISS] encoder unavailable (model={self.embed_model}, local_only={self.local_only}), fallback lexical",
                    flush=True,
                )
            return None
        try:
            if self.debug:
                print(
                    f"[BEST_OF_N][FAISS] building index lines={len(self.original_lines)} model={self.embed_model}",
                    flush=True,
                )
            vecs = encoder.encode(self.original_lines, convert_to_numpy=True, show_progress_bar=False)
            arr = np.asarray(vecs, dtype="float32")
            arr = self._normalize_vecs(arr)
            dim = int(arr.shape[1])
            index = faiss.IndexFlatIP(dim)
            index.add(arr)
            payload = {
                "index": index,
                "lines": list(self.original_lines),
            }
            self._INDEX_CACHE[key] = payload
            if self.debug:
                print("[BEST_OF_N][FAISS] index ready", flush=True)
            return payload
        except Exception as e:
            if self.debug:
                print(f"[BEST_OF_N][FAISS] build failed: {e}; fallback lexical", flush=True)
            return None

    def _vector_best_similarity(self, query: str) -> float:
        payload = self._faiss_payload
        if payload is None or np is None or faiss is None:
            return 0.0
        encoder = self._get_encoder(self.embed_model)
        if encoder is None:
            return 0.0
        try:
            q = encoder.encode([query], convert_to_numpy=True, show_progress_bar=False)
            q_arr = np.asarray(q, dtype="float32")
            q_arr = self._normalize_vecs(q_arr)
            scores, _ = payload["index"].search(q_arr, 1)
            raw_score = float(scores[0][0])
            # cosine/IP -> [-1,1], map into [0,1]
            return max(0.0, min(1.0, (raw_score + 1.0) / 2.0))
        except Exception:
            return 0.0

    def _best_similarity(self, query: str, candidates: List[str]) -> float:
        if self._faiss_payload is not None and (candidates is self.original_lines or candidates == self.original_lines):
            v = self._vector_best_similarity(query)
            if v > 0:
                return v
        return _best_similarity_lexical(query, candidates)

    def _score_structure(self, bullets: List[str]) -> float:
        if not bullets:
            return 0.0
        count = len(bullets)
        if 2 <= count <= 5:
            count_score = 1.0
        elif count == 1:
            count_score = 0.55
        else:
            count_score = 0.75

        avg_words = sum(len(b.split()) for b in bullets) / max(len(bullets), 1)
        if 11 <= avg_words <= 34:
            length_score = 1.0
        elif 8 <= avg_words <= 44:
            length_score = 0.8
        else:
            length_score = 0.55
        return (count_score + length_score) / 2.0

    def _score_skill_alignment(self, text: str) -> float:
        if not self.skill_memory:
            return 0.6
        if self._faiss_payload is not None:
            # semantic alignment with source as additional signal for skill relevance
            sem = self._vector_best_similarity(text)
            lex_hits = 0
            for s in self.skill_memory:
                if _contains_term(s, text):
                    lex_hits += 1
            lex = min(lex_hits / max(min(4, len(self.skill_memory)), 1), 1.0)
            return (sem * 0.55) + (lex * 0.45)
        hits = 0
        for s in self.skill_memory:
            if _contains_term(s, text):
                hits += 1
        target = min(4, len(self.skill_memory))
        return min(hits / max(target, 1), 1.0)

    def _score_faithfulness(self, title: str, draft: str, bullets: List[str]) -> float:
        # lexical overlap on whole candidate
        cand_text = " ".join([title, draft] + bullets)
        cand_tokens = _tokenize(cand_text)
        token_overlap = _jaccard(cand_tokens, self._source_tokens)

        if not bullets or not self.original_lines:
            line_support = self._best_similarity(cand_text, self.original_lines)
            return (token_overlap * 0.45) + (line_support * 0.55)

        bullet_support_scores = [self._best_similarity(b, self.original_lines) for b in bullets]
        bullet_support = sum(bullet_support_scores) / max(len(bullet_support_scores), 1)
        draft_support = self._best_similarity(draft, self.original_lines)
        return (token_overlap * 0.30) + (draft_support * 0.25) + (bullet_support * 0.45)

    def score_candidate(self, index: int, item: Dict[str, object]) -> CandidateScore:
        title = str(item.get("title", "")).strip()
        draft = str(item.get("draft", "")).strip()
        bullets_raw = item.get("bullets", [])
        bullets = (
            [str(x).strip() for x in bullets_raw if str(x).strip()]
            if isinstance(bullets_raw, list)
            else []
        )

        star = 0.0
        if bullets:
            star = sum(_star_score(b) for b in bullets) / max(len(bullets), 1)
        faith = self._score_faithfulness(title, draft, bullets)
        skill = self._score_skill_alignment(" ".join([title, draft] + bullets))
        structure = self._score_structure(bullets)

        # favor faithfulness + STAR first
        total = (faith * 0.42) + (star * 0.33) + (skill * 0.20) + (structure * 0.05)
        return CandidateScore(
            index=index,
            total=total,
            star=star,
            faithfulness=faith,
            skill_alignment=skill,
            structure=structure,
        )

    def select(self, candidates: List[Dict[str, object]]) -> Tuple[Dict[str, object], Dict[str, object]]:
        if not candidates:
            return {"title": "", "draft": "", "bullets": []}, {
                "candidate_count": 0,
                "selected_index": -1,
                "scores": [],
            }

        scored = [self.score_candidate(i, c) for i, c in enumerate(candidates)]
        ranked = sorted(
            scored,
            key=lambda x: (x.total, x.faithfulness, x.star, x.skill_alignment),
            reverse=True,
        )
        best = ranked[0]
        report = {
            "candidate_count": len(candidates),
            "selected_index": best.index,
            "scores": [x.as_dict() for x in ranked],
        }
        return candidates[best.index], report
