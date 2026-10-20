# Project Context: AI University Project Reviewer

## Project goal
A local-first, read-only CLI to help a teaching assistant review student submissions for Artificial Intelligence, academic year 2026/27, Assignment 1 (Uninformed Search Techniques). It must support Social Golfers, Sudoku, Latin Square, and Search Trees. It should report evidence and limitations, never invent official grades or declare plagiarism. It does not execute untrusted student code.

## Current workspace/state
Project root: `C:\Users\erbli\OneDrive\Desktop\ai-agent`. Python package lives in `src/reviewer`; Assignment 1 configuration is `assignments/2026-27/assignment-01.yaml`; tests and ordinary synthetic submission fixtures are under `tests/fixtures`; usage is in `README.md`. This is an existing Git working tree. Continue modifying it directly; do not create another repository or nested project.

## What is implemented
- CLI: `review-local` / `review-github`, task filter, Markdown + JSON reports, assignment YAML loading, explicit GitHub repo lists or configured repo list and org/account discovery.
- Local ingestion is read-only, ignores symlinks/tool cache directories, records Git commit and local tree digest, and rejects report output paths inside a submitted local repo.
- GitHub REST client includes read-only GETs, token from `GITHUB_TOKEN`, pagination, retries/timeouts, commit-pinned content retrieval and history metadata. API pagination, snapshot behavior, and auth header have mock tests. No live GitHub access has been tested; no API-content cache.
- Output extraction does not require a special reviewer JSON file. It accepts named JSON files/task-keyed `outputs`, Python literal output constants without executing code, matrix CSV/TXT for Latin/Sudoku, and JSON trees for 8-Puzzle, Missionaries/Cannibals, and rotating workforce. `review-evidence.json` remains an optional convenience format.
- Deterministic validators check Social Golfers group sizes/coverage/repeated pairs/week count, Sudoku rows/columns/boxes/clue preservation and difficulty coverage, Latin Square dimensions/symbols/rows/columns, and structured search-tree states/transitions. Search trees accept configurable generic workforce checks; no workforce rules are assumed unless supplied in config. Diagram formats remain manual review.
- Python AST algorithm analysis reports structural evidence only. It avoids treating comments or names as proof and does not misclassify ordinary stack `.pop()` as BFS. Valid output is kept separate from algorithm evidence; AST evidence is repository-wide and may be unrelated to the selected task, so manual path attribution is required. No language besides Python is analyzed.
- Search-space reports show explicit raw upper bounds for Latin/Sudoku and unlabeled weekly partitions for Social Golfers, with assumptions. Social Golfers validity is not an optimality/max-weeks proof.
- Provisional rubric has no weights. Scores are withheld until the instructor configures an approved rubric. `rubrics/assignment-01-framework.yaml` is an unapproved qualitative template; all weights are unset. Similarity reports are human-review leads only, with exact/normalized files and matching 4-line fragments; no plagiarism finding or penalty is automatic. `scc` runs if installed; it was not confirmed available in this environment.
- Optional AI interpretation is implemented through an OpenAI-compatible Chat Completions provider. It is opt-in per CLI and disabled by default in `config/reviewer.yaml`. Source upload requires both config `llm.allow_source_upload: true` and CLI `--allow-source-upload`; otherwise source excerpts are omitted. Sensitive-looking files are skipped, common secret patterns are redacted, and a configured size cap applies. AI output is a distinct qualitative report section with schema/field/citation validation and cannot produce scores. Provider calls have mock coverage only; no live LLM integration was tested.

## Important files
- `src/reviewer/cli.py`: command line and repository scope
- `src/reviewer/ingestion.py`, `github.py`: local/GitHub retrieval
- `src/reviewer/evidence.py`: conventional data extraction without executing code
- `src/reviewer/validators.py`: deterministic validators
- `src/reviewer/algorithms.py`: conservative AST clues
- `src/reviewer/orchestration.py`, `reporting.py`: findings and reports
- `src/reviewer/grading.py`, `similarity.py`, `specs.py`: scoring, similarity, config validation
- `assignments/2026-27/assignment-01.yaml`: editable task/rubric/scope config
- `tests/test_core.py`, `tests/fixtures/*`: synthetic and integration coverage

## Verified at latest audit
Latest run: `python -m pytest -q` -> 33 passed. `python -m compileall -q src tests` passed; `python -m reviewer.cli --help` worked; a `review-local tests\fixtures\conventional --task all` smoke test emitted both JSON and Markdown reports; `git diff --check` passed. Tests include all four task report generation, correct/invalid outputs, incomplete Sudoku levels, misleading and incorrect BFS claims, invalid tree transitions, ordinary fixture directories, mocked GitHub and LLM calls, upload authorization/citation checks, and output-path safety. Do not claim live GitHub, live LLM, or SCC functionality has been exercised.

## Commands
From PowerShell at project root:

```powershell
python -m pytest -q
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m reviewer.cli --help
python -m reviewer.cli review-local C:\path\to\submission --task all --out reports
$env:GITHUB_TOKEN = 'read-only-token'
python -m reviewer.cli review-github --repo course/student-repo --task all --out reports
```

Installable entry point after `pip install -e .`: `ai-reviewer review-local ...`. Keep report `--out` outside every local submission directory.

## Prompting guidance for the next coding session
Ask for one focused outcome, name acceptance checks, and ask for the actual edits plus tests in the same prompt. Example:

> Continue in the existing workspace; do not rebuild or create another repo. Implement [specific missing feature]. Preserve the no-student-code-execution rule and keep output validity separate from algorithm evidence. Add a focused fixture/test, run `python -m pytest -q`, compilation, and a CLI smoke test; fix failures and report verified limits.

Good next priorities: inspect/finish requirement-specific academic evidence checks, improve task attribution for Python AST findings, add local cache outside submitted trees, test GitHub rate-limit/truncated-tree handling, and refine rubric criteria validation. Do not add official score weights, assume a language, execute student projects, or infer rotating-workforce constraints.

For a portable project overview and prompting tips, see [PROJECT_SUMMARY_FOR_CHATGPT.md](PROJECT_SUMMARY_FOR_CHATGPT.md).
