# VS Code Agent Instructions (Research Synth)

## Goal
Implement and extend a Python CLI tool named `research-synth` with a stable, testable foundation.
Do NOT build a VS Code extension. This is CLI-first.

## Non-negotiables
- Keep code in `src/research_synth/` using a package layout.
- All dependencies must run inside a project-local `.venv`.
- Pin dependencies in `pyproject.toml` (no floating ranges).
- Keep the core data schema in `models.py` stable; avoid breaking changes.
- Use `research.yml` as the per-project config. No hidden global config.
- `USER_MANUAL.md` is authoritative for usage/workflow; do not contradict it.

## Setup steps (agent should run)
1. Create `.venv` in repo root:
   - Windows PowerShell: `py -m venv .venv`
   - Activate: `.venv\Scripts\Activate.ps1`
2. Install in editable mode:
   - `pip install -e .`
3. Run tests:
   - `pip install pytest`
   - `pytest -q`

## Commands to verify
- `research-synth --help`
- `research-synth init . --name "My Project"`
- `research-synth ingest .` (after placing at least one file in `sources/`)
- `research-synth analyze .` (after ingest produces chunks/extracted_text.json)

## Implementation guidance
- Prefer boring, readable Python.
- Add new commands under `src/research_synth/commands/`.
- Any command that writes outputs must write to the active project folder (NOT the tool repo).
- Add caching via `.research_cache` for expensive work.
- Do not add environment managers or installers.

## Anti-patterns (do not do)
- Do not add VS Code extension scaffolding.
- Do not embed credentials in code or configs.
- Do not store outputs outside the project folder.


## LLM test (manual only)
To validate OpenAI mode (requires API key and network access):
- Set `OPENAI_API_KEY`
- Run: `research-synth analyze . --mode openai --model gpt-4o-mini`
