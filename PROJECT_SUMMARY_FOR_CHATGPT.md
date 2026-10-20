# AI University Project Reviewer — handoff context

Paste this file into a browser ChatGPT chat to give it project context. It describes the current workspace as of 2026-10-20; ask Codex to verify current files before making claims about later changes.

## Goal and guardrails

This is an existing Python 3.11+ read-only CLI in `C:\Users\erbli\OneDrive\Desktop\ai-agent` for reviewing AI 2026/27 Assignment 1 student submissions. Work directly in this repository. Do not rebuild the project, create nested/separate Git repositories, execute student code, invent assignment requirements or grading weights, or automatically declare plagiarism. Keep deterministic output validation separate from algorithm evidence. Similarity leads require human review.

## Current implementation

- Commands: `review-local` and `review-github`; both produce Markdown and JSON reports.
- Four task validators: Social Golfers schedule coverage/group/pair constraints; Sudoku rows/columns/boxes/clue preservation; Latin Square dimensions/domain/row/column uniqueness; and structured search trees for 8-Puzzle and Missionaries/Cannibals. Rotating Workforce checks apply only when configured; no rules are presumed.
- Submission evidence is extracted from ordinary supported files: named/task-keyed JSON, optional `review-evidence.json`, Python top-level literal constants parsed without executing code, and CSV/TXT matrix files. Diagram formats and unsupported result formats require manual review.
- Python AST analysis reports structural DFS/BFS/IDDFS/backtracking clues only. It does not prove runtime algorithm behavior and does not analyze non-Python languages. Task attribution remains repository-wide and needs human confirmation.
- Similarity compares repositories in the same invocation using exact/normalized file hashes and normalized four-line fragments. Configurable exclusions/starter code exist. Similarity does not establish misconduct.
- GitHub uses read-only REST GETs, `GITHUB_TOKEN`, pagination, retries/timeouts, pinned commit snapshots, and history metadata. It has mock coverage only; live GitHub access is unverified.
- `scc` metrics are collected when the executable is installed; unavailable/failing `scc` is reported. Its presence was not confirmed in the last environment check.
- Numeric scoring is withheld with the default provisional rubric. `rubrics/assignment-01-framework.yaml` is an unapproved qualitative template with all weights unset.
- `config/reviewer.yaml` defines reviewer role, skills, rules, workflow, evidence requirements, Definition of Done, and optional AI policy.
- Optional AI is an OpenAI-compatible Chat Completions provider (`src/reviewer/llm.py`), separately requested with `--ai-review`; deterministic review needs no model. Base URL/model/key come from environment. Local-compatible endpoints are supported without a key only for localhost addresses. Source is sent only if both config `llm.allow_source_upload: true` and CLI `--allow-source-upload` are present. Sensitive-looking filenames are excluded, common secret patterns are redacted, and source size is capped. AI output is schema/field/citation validated, remains a separate qualitative section, and cannot create scores. Live model integration is unverified; provider calls are mocked in tests.
- Local report output cannot be written inside a reviewed submission. Local ingestion is read-only and skips common generated/dependency/cache directories.

## Useful commands (PowerShell, run from project root)

```powershell
python -m pytest -q
python -m compileall -q src tests
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m reviewer.cli --help
python -m reviewer.cli review-local C:\path\to\student-submission --task all --out reports
python -m reviewer.cli review-local C:\path\to\student-submission --task sudoku --out reports
```

Installable command after `pip install -e .`: `ai-reviewer review-local ...`. GitHub example: `ai-reviewer review-github --repo course/student --task all --out reports`; set `GITHUB_TOKEN` in the environment for private repositories. Optional compatible model example: set `AI_REVIEW_BASE_URL`, `AI_REVIEW_MODEL`, and (for nonlocal provider) `AI_REVIEW_API_KEY`; use a reviewer config with `llm.enabled: true`, then pass `--ai-review`. Keep private source upload disabled unless both upload opt-ins have been deliberately configured.

## Latest verified state

At the latest full run, `python -m pytest -q` passed 33 tests, `python -m compileall -q src tests` passed, CLI `--help` worked, and a conventional-fixture `review-local --task all` smoke test emitted both report formats. `git diff --check` passed. The tests mock GitHub and LLM calls; no live service calls have been verified.

## Most useful next prompt for Codex

Ask for one concrete outcome and acceptance checks, e.g. “Continue in the existing workspace. Inspect current status first. Fix [specific issue] without executing student code or weakening privacy gates. Add focused tests, run the full suite, compileall, and a CLI smoke test, then report actual outcomes and remaining limitations.” Codex should verify the latest files rather than relying on this summary if the workspace has changed.
