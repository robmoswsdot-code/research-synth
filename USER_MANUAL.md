# Research-Synth User Manual

## Purpose
Research-Synth is a CLI-based research synthesis tool designed to accelerate document review and drafting while preserving traceability.
It is not a final report generator. It produces structured draft artifacts for human review.

## Core Principles
- Boring, reliable, repeatable
- File-based and auditable
- Human-in-the-loop
- Enterprise-safe (no global installs, no network-drive execution)

## Architecture Overview
There are three distinct layers:
1. Tool repository (reusable, local)
2. Research run folder (project-specific, local working copy)
3. Systems of record (Share Drive / ProjectWise)

Do not mix these layers.

## Tool Location
The tool lives locally, outside synced folders:
`C:\Users\<you>\source\repos\research-synth`

The virtual environment (`.venv`) lives inside the tool repo.

## Research Run Location
Each research effort gets its own local working directory, e.g.:
`D:\Work\ResearchRuns\SR-204\2026-01`

This directory contains:
- `sources/`
- `outputs/`
- `chunks/`
- `.research_cache/`
- `research.yml`

## Installation
1. Create and activate a virtual environment in the tool repo.
2. Install in editable mode: `pip install -e .`
3. Run tests: `pytest`
4. Verify: `research-synth --help`

## Optional extras
Some features are provided as optional dependency *extras* that are not required for the core CLI. Install extras with:

```powershell
pip install -e .[tokens,pdf,excel]
```

- `tokens`: installs `tiktoken` for token-aware chunking (recommended when available). The code includes a **whitespace-tokenizer fallback** so the tool works without `tiktoken` installed.
- `pdf`: installs `pymupdf` for PDF extraction. On some Windows environments a native build may be required if a prebuilt wheel is unavailable — prefer installing these extras on platforms with available wheels.
- `excel`: installs `pandas` + `openpyxl` for Excel extraction.

Note: extras may increase install size and, in some environments, require platform-specific toolchains; only install extras you need.

## Creating a Research Run
1. Create a local working folder.
2. `cd` into that folder.
3. Run: `research-synth init . --name "<project name>"`

## Configuration
`research.yml` controls project behavior. Edit it manually as needed.

## Workflow
1. Export documents from ProjectWise / Share Drive.
2. Place copies into `sources/`.
3. Run `ingest` to extract and chunk text.
4. Run `analyze` to produce heuristic concepts (no LLM) into `analysis/concepts.json`.
5. Review generated drafts.
6. Publish outputs to Share Drive or ProjectWise.

## Caching
`.research_cache` stores expensive intermediate results. It can be deleted safely to force a clean run.

## What This Tool Will Not Do
- Make engineering or policy decisions
- Produce publish-ready reports without review
- Replace professional judgment

## Correct Usage Summary
- Tool code: local
- Working data: local
- Team review: Share Drive
- Official record: ProjectWise


## LLM Mode (Optional)
`analyze` can run in an OpenAI-backed mode for higher quality concept extraction.

### Requirements
- Network access to the OpenAI API endpoint
- `OPENAI_API_KEY` set in your environment

### Usage
```powershell
$env:OPENAI_API_KEY = "YOUR_KEY_HERE"
research-synth analyze . --mode openai --model gpt-4o-mini --max-concepts 50
```

If you cannot use external network calls, keep using `--mode heuristic`.
