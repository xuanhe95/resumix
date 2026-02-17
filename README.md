# Standalone Resume Agent

Independent AI pipeline project for:

1. reading resume PDF
2. LLM section classification (`personal_info`, `education`, `experience`, `skills`, `projects`)
3. skills fact extraction + whitelist matching from `tech_stack_set.txt`
4. passthrough output for `personal_info` / `education` / `skills` (no polishing)
5. draft summary + bullet generation for `experience` / `projects`
6. STAR-style bullet sanity check
7. evidence-based critic (evidence/fact consistency check for each bullet)
8. missing skill suggestion generation
9. persistent user memory (stored under `memory/`)
10. final JSON record exporter (stored under `records/`)
11. standalone colored resume report in terminal

This folder does not depend on `resumix` business modules, but keeps an LLM caller structure similar to your current project (`LLMClient`, `generate`, `generate_json`).

## 1) Setup

```bash
cd /Users/xander/Documents/git/resumix
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install python-dotenv requests pymupdf langchain langgraph
# Optional but recommended for evidence vector retrieval:
pip install faiss-cpu sentence-transformers
```

## 2) Configure env

Copy and edit:

```bash
cp /Users/xander/Documents/git/resumix/resume_agent_standalone/.env.example /Users/xander/Documents/git/resumix/resume_agent_standalone/.env
```

You can use:
- local ollama (`LOCAL_LLM_URL`)
- Modal OpenAI-compatible endpoint (`MODAL_OPENAI_API_URL`)
- custom skill whitelist file (`TECH_STACK_SET_FILE`)
- persistent user memory file (`USER_MEMORY_FILE`, default under `memory/user_memory.json`)
- final records folder (`RECORDS_DIR`) and save switch (`SAVE_FINAL_RECORD=1`)
- bullet generation mode switch (`BULLETS_FROM_DRAFT_ONLY=1` to force per-draft LLM generation)
- best-of-n switch (`BEST_OF_N_ENABLED=1`, `BULLET_CANDIDATE_COUNT=3`) to generate multi-candidates and auto-select best one
- best-of-n FAISS scoring (`BEST_OF_N_USE_FAISS=1`, `BEST_OF_N_EMBED_MODEL=...`)
- evidence critic thresholds (`EVIDENCE_*`) for grounding checks
- FAISS retrieval switch (`EVIDENCE_USE_FAISS=1`) and embedding model (`EVIDENCE_EMBED_MODEL=...`)
- embedding load mode (`EMBED_LOCAL_ONLY=1` avoids first-run download stalls; set `0` to allow download)
- vector debug logs (`VECTOR_DEBUG=1`)

## 3) Run

```bash
cd /Users/xander/Documents/git/resumix/resume_agent_standalone
python run.py --resume /absolute/path/to/resume.pdf --direction "Backend Engineer"
```

You can also run interactive mode:

```bash
python run.py --resume /absolute/path/to/resume.pdf --interactive
```

## 4) New deterministic chain

`run.py` now executes this pipeline by default with LangGraph:

1. `parse_resume_sections`
2. `extract_skills_facts`
3. `passthrough_base_sections`
4. `summarize_experience` -> `build_experience_bullets` -> `compose_experience_json`
5. `summarize_projects` -> `build_projects_bullets` -> `compose_projects_json`
6. `suggest_missing_skills`
7. output final combined JSON

Every step prints color-coded logs in terminal.

After pipeline completion:
- Final JSON is saved to `records/<profile_name>_<timestamp>.json`
- A standalone colorized "Resume Report" is printed in terminal

`experience/projects` item payload now includes:
- `evidence_summary`
- `evidence_reports`

In interactive mode, you can inspect evidence checks directly:

```bash
evidence experience
evidence projects
```

Persistent memory commands:

```bash
memory_show
memory_update {"tone":"concise","target_roles":["Backend Engineer"]}
memory_update 不要改skills，必须保留: Company name, Redis
memory_clear
```
