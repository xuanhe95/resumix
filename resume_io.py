from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Union

import fitz

try:
    from rapidfuzz import fuzz as rf_fuzz
except Exception:
    rf_fuzz = None


@dataclass
class ResumeState:
    resume_path: str = ""
    resume_text: str = ""
    sections: Dict[str, List[str]] = field(default_factory=dict)
    target_direction: str = "General"
    rewritten_sections: Dict[str, str] = field(default_factory=dict)
    facts: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    skill_memory: List[str] = field(default_factory=list)
    skill_facts: List[str] = field(default_factory=list)
    section_summaries: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    section_bullets: Dict[str, List[Dict[str, object]]] = field(default_factory=dict)
    final_section_json: Dict[str, Dict[str, object]] = field(default_factory=dict)
    skill_suggestions: List[str] = field(default_factory=list)
    locked_facts: Dict[str, List[str]] = field(default_factory=dict)
    fact_validation_reports: Dict[str, Dict[str, object]] = field(
        default_factory=dict
    )
    rewrite_status: Dict[str, Dict[str, object]] = field(default_factory=dict)
    last_raw_parse: str = ""
    persistent_memory: Dict[str, object] = field(default_factory=dict)
    memory_file: str = ""


def read_pdf_text(path: str, max_pages: int = 3) -> str:
    doc = fitz.open(path)
    chunks: List[str] = []
    for i in range(min(max_pages, len(doc))):
        chunks.append(doc.load_page(i).get_text("text"))
    return "\n".join(chunks).strip()


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


def split_bullets(text: str) -> List[str]:
    lines: List[str] = []
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        s = re.sub(r"^[\-•\*\d\.\)\(]+\s*", "", s).strip()
        if s:
            lines.append(s)
    return lines


def _is_section_header(line: str) -> str:
    s = re.sub(r"[:：\-\s]+$", "", (line or "").strip().lower())
    mapping = {
        "personal info": "personal_info",
        "personal information": "personal_info",
        "contact": "personal_info",
        "education": "education",
        "experience": "experience",
        "work experience": "experience",
        "professional experience": "experience",
        "projects": "projects",
        "project": "projects",
        "skills": "skills",
        "technical skills": "skills",
        "awards": "awards",
        "honors": "awards",
    }
    return mapping.get(s, "")


def parse_sections_by_rules(text: str) -> Dict[str, List[str]]:
    """
    Rule-based parser to preserve all lines under each section heading.
    This complements LLM parsing when the model over-compresses bullets.
    """
    keys = ["personal_info", "education", "experience", "projects", "skills", "awards"]
    out: Dict[str, List[str]] = {k: [] for k in keys}

    current = "personal_info"
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        hdr = _is_section_header(line)
        if hdr:
            current = hdr
            continue

        # Normalize bullet prefix but keep full textual content.
        clean = re.sub(r"^[\-•\*\d\.\)\(]+\s*", "", line).strip()
        if not clean:
            continue

        # Merge wrapped continuation lines into previous bullet for exp/projects.
        if (
            current in {"experience", "projects"}
            and out[current]
            and not re.match(r"^[A-Z][A-Za-z0-9].{0,40},", clean)
            and len(clean) < 100
            and not clean.lower().startswith(("http", "www"))
            and clean[0].islower()
        ):
            out[current][-1] = f"{out[current][-1]} {clean}".strip()
        else:
            out[current].append(clean)

    return {k: _dedupe_lines(v) for k, v in out.items()}


def _merge_parsed_sections(
    rules_sections: Dict[str, List[str]], llm_sections: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    keys = ["personal_info", "education", "experience", "projects", "skills", "awards"]
    merged: Dict[str, List[str]] = {}
    for k in keys:
        rr = rules_sections.get(k, [])
        ll = llm_sections.get(k, [])
        # For experience/projects, prefer rule parser to keep full bullet coverage.
        if k in {"experience", "projects"} and rr:
            merged[k] = _dedupe_lines(rr + ll)
        else:
            merged[k] = _dedupe_lines(rr + ll if rr else ll)
    return merged


def _dedupe_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in lines:
        v = str(x).strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def extract_section_facts(lines: List[str], llm) -> Dict[str, List[str]]:
    """Use LLM to extract hard and soft facts from section lines."""
    text = "\n".join(lines).strip()
    if not text:
        return {"hard_facts": [], "soft_facts": []}

    prompt = (
        "Extract facts from the resume section text and split into hard and soft facts.\n"
        "hard_facts: concrete/verifiable surface forms that should remain exact, such as:\n"
        "- names, organizations, job titles\n"
        "- dates/years/durations\n"
        "- numbers/percentages/counts\n"
        "- technologies/tools/certifications\n"
        "- emails/links\n"
        "soft_facts: semantic statements that may be paraphrased but should keep meaning.\n"
        "Do NOT invent facts. Keep hard_facts in exact text surface forms from input.\n"
        'Return strict JSON only: {"hard_facts": ["..."], "soft_facts": ["..."]}\n\n'
        f"SECTION_TEXT:\n{text}"
    )
    raw = llm.generate_json(prompt)
    data = _extract_json_obj(raw)

    hard_facts = (
        data.get("hard_facts", [])
        if isinstance(data, dict) and isinstance(data.get("hard_facts", []), list)
        else []
    )
    soft_facts = (
        data.get("soft_facts", [])
        if isinstance(data, dict) and isinstance(data.get("soft_facts", []), list)
        else []
    )
    hard_out = _dedupe_lines(hard_facts)
    soft_out = _dedupe_lines(soft_facts)
    if hard_out or soft_out:
        return {"hard_facts": hard_out, "soft_facts": soft_out}

    # Fallback: keep original lines as hard facts and no soft facts.
    fallback = _dedupe_lines(lines)
    print(f"facts fallback (hard): {fallback}")
    return {"hard_facts": fallback, "soft_facts": []}


def extract_hard_facts(lines: List[str], llm) -> List[str]:
    """Compatibility wrapper for existing call sites."""
    return extract_section_facts(lines, llm).get("hard_facts", [])


def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[\u2013\u2014]", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _best_similarity_against_text(fact: str, text: str) -> float:
    fact_n = _normalize_text(fact)
    text_n = _normalize_text(text)
    if not fact_n or not text_n:
        return 0.0

    lines = split_bullets(text_n)
    candidates = lines if lines else [text_n]

    best = 0.0
    for cand in candidates:
        if rf_fuzz is not None:
            score = float(rf_fuzz.token_set_ratio(fact_n, cand))
        else:
            score = SequenceMatcher(None, fact_n, cand).ratio() * 100.0
        if score > best:
            best = score
    return round(best, 2)


def validate_rewrite_against_facts(
    required_facts: Union[List[str], Dict[str, List[str]]], rewritten_text: str
) -> Tuple[bool, Dict[str, object]]:
    """Validate rewrite with fuzzy matching for both hard and soft facts."""
    rewritten = rewritten_text or ""
    rewritten_norm = _normalize_text(rewritten)

    if isinstance(required_facts, dict):
        hard_facts = required_facts.get("hard_facts", []) or []
        soft_facts = required_facts.get("soft_facts", []) or []
    else:
        hard_facts = required_facts or []
        soft_facts = []

    hard_scores: List[Dict[str, object]] = []
    hard_threshold = _env_float("FACT_HARD_MATCH_THRESHOLD", 92.0)
    missing_hard: List[str] = []
    for fact in hard_facts:
        fact_norm = _normalize_text(str(fact))
        if not fact_norm:
            continue
        score = 100.0 if fact_norm in rewritten_norm else _best_similarity_against_text(str(fact), rewritten)
        hard_scores.append({"fact": str(fact), "score": round(score, 2)})
        if score < hard_threshold:
            missing_hard.append(str(fact))

    soft_scores: List[Dict[str, object]] = []
    soft_threshold = _env_float("FACT_SOFT_MATCH_THRESHOLD", 82.0)
    for fact in soft_facts:
        score = _best_similarity_against_text(str(fact), rewritten)
        soft_scores.append({"fact": str(fact), "score": score})

    low_conf_soft = [x["fact"] for x in soft_scores if float(x["score"]) < soft_threshold]
    soft_total = len(soft_facts)
    soft_passed = soft_total - len(low_conf_soft)
    soft_coverage = round((soft_passed / soft_total), 4) if soft_total > 0 else 1.0
    soft_required_coverage = _env_float("FACT_SOFT_REQUIRED_COVERAGE", 0.8)

    ok = len(missing_hard) == 0 and soft_coverage >= soft_required_coverage
    report = {
        "required_hard_facts": hard_facts,
        "required_soft_facts": soft_facts,
        "missing_hard_facts": missing_hard,
        "hard_fact_scores": hard_scores,
        "hard_match_threshold": hard_threshold,
        "soft_fact_scores": soft_scores,
        "low_confidence_soft_facts": low_conf_soft,
        "soft_match_threshold": soft_threshold,
        "soft_coverage": soft_coverage,
        "soft_required_coverage": soft_required_coverage,
    }

    return ok, report


def normalize_sections(data: Dict) -> Dict[str, List[str]]:
    keys = ["personal_info", "education", "experience", "projects", "skills", "awards"]
    out: Dict[str, List[str]] = {k: [] for k in keys}
    for k in keys:
        v = data.get(k, [])
        if isinstance(v, list):
            out[k] = [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v, str) and v.strip():
            out[k] = [x.strip("-• ").strip() for x in v.splitlines() if x.strip()]
    return _reclassify_misplaced_lines(out)


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def _reclassify_misplaced_lines(sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Post-process LLM parse results to fix common misclassification.
    """
    out = {k: list(v) for k, v in sections.items()}

    skill_kw = [
        "skills",
        "programming",
        "language:",
        "languages:",
        "framework",
        "frameworks",
        "tools",
        "tech stack",
        "database",
        "cloud",
        "kubernetes",
        "docker",
        "java",
        "python",
        "golang",
        "c++",
    ]
    personal_kw = ["email", "phone", "github", "linkedin", "portfolio", "@", "www.", "http"]

    # Move skill-like lines out of personal_info.
    kept_personal: List[str] = []
    for line in out.get("personal_info", []):
        if _contains_any(line, skill_kw) and not _contains_any(line, personal_kw):
            out["skills"].append(line)
        else:
            kept_personal.append(line)
    out["personal_info"] = kept_personal

    # Move contact-like lines accidentally placed in skills back to personal_info.
    kept_skills: List[str] = []
    for line in out.get("skills", []):
        if _contains_any(line, personal_kw) and not _contains_any(line, skill_kw):
            out["personal_info"].append(line)
        else:
            kept_skills.append(line)
    out["skills"] = kept_skills

    # Deduplicate while preserving order.
    for key in out:
        deduped: List[str] = []
        seen = set()
        for line in out[key]:
            val = line.strip()
            if not val or val in seen:
                continue
            seen.add(val)
            deduped.append(val)
        out[key] = deduped

    return out


def parse_sections_by_llm(text: str, llm) -> Dict[str, List[str]]:
    if len((text or "").strip()) < 30:
        return {
            k: []
            for k in [
                "personal_info",
                "education",
                "experience",
                "projects",
                "skills",
                "awards",
            ]
        }

    prompt = (
        "Parse the following resume text and return strict JSON only.\n"
        "Keys must be: personal_info, education, experience, projects, skills, awards.\n"
        "Each value must be an array of concise strings. Missing keys use [].\n"
        "Do not invent any person identity (e.g., John Doe), company, date, or skill "
        "that is not explicitly present in RESUME_TEXT.\n\n"
        f"RESUME_TEXT:\n{text}"
    )
    rules_sections = parse_sections_by_rules(text)
    raw = llm.generate_json(prompt)
    print("Raw Data")
    print(raw)
    data = _extract_json_obj(raw)

    if data:
        llm_sections = normalize_sections(data)
        return _merge_parsed_sections(rules_sections, llm_sections)
    # repair pass
    repair = llm.generate_json(
        "Convert this text to valid JSON with keys personal_info, education, "
        "experience, projects, skills, awards; values as arrays of strings.\n\n" + raw
    )
    data = _extract_json_obj(repair)

    print(data)
    if data:
        llm_sections = normalize_sections(data)
        return _merge_parsed_sections(rules_sections, llm_sections)
    return rules_sections
