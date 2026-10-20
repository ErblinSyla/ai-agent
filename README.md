# AI University Project Reviewer

Read-only CLI MVP for Artificial Intelligence 2026/27 Assignment 1. The reviewer checks supplied outputs, identifies static source-code clues for required algorithms, validates supported search-tree representations, and writes Markdown and JSON reports. It does not execute student code or replace instructor judgment.

## Install and run

From the project root, with Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest -q
python -m compileall -q src tests
ai-reviewer --help
```

See the complete Windows walkthrough in [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md), including setting up a separate student repository, local/GitHub review, and Groq-compatible AI configuration. This repository does not contain the student's assignment solution.

Select one task with `--task social_golfers`, `sudoku`, `latin_square`, or `search_trees`. The default is `all`. Pass an alternate spec with `--assignment C:\path\assignment.yaml`. Reports are written as `<repository>.json` and `.md`. Report output is rejected if it resolves inside a local submission directory. No numeric score is produced while the rubric is provisional or absent.

## Accepted evidence formats

Student source is always read statically. The reviewer never imports or executes it.

- **Python source:** literal top-level output constants can be extracted without execution. Examples: `LATIN_SQUARE = [[1,2],[2,1]]`, `SOCIAL_GOLFERS_SCHEDULE = [[[0,1],[2,3]]]`, `SUDOKU_SOLUTION` plus `SUDOKU_CLUES`, and a named tree constant such as `EIGHT_PUZZLE_TREE`.
- **CSV/TXT matrices:** Latin files named with `latin` (for example `latin_square.csv`); Sudoku puzzle/solution files whose names include `sudoku` and `clues`/`puzzle` or `solution`. One integer matrix row per line; commas or whitespace are accepted. Difficulty-tagged Sudoku names such as `easy_sudoku_clues.csv`, `easy_sudoku_solution.csv`, and matching `medium`/`hard` files are grouped into fixtures.
- **JSON:** a root `outputs` object keyed by task id; a task-keyed object; files named `social_golfers.json`, `sudoku.json`, `latin_square.json`, or `search_trees.json`; and individual tree files named `eight_puzzle.json`, `missionaries_cannibals.json`, or `rotating_workforce.json`.
- **Portable search-tree object:** `initial`, `goal`, `states`, and `edges`; each edge is `{ "from": state, "to": state, "action": label }`. 8-Puzzle uses a flat 9-element or 3x3 state. Missionaries/Cannibals uses `[missionaries_left, cannibals_left, boat_side]` with 0=left and 1=right. Workforce checks are configurable in the assignment spec; no unstated schedule rules are presumed.
- **Optional convenience format:** `review-evidence.json` may hold `{ "outputs": { ... } }` in the same task formats. It is not required.

A solver implemented as executable functions does not yield a verified answer unless a result fixture/output is also supplied. In that case output validation is marked unavailable/manual review. Sudoku clues and solutions must be full 9x9 matrices for the default 3x3 boxes. When only one valid Sudoku is supplied, output validity can pass while coverage of Easy/Medium/Hard remains marked for manual review. All difficulty fixtures can be supplied under `sudoku.fixtures` in JSON or with difficulty-tagged CSV files.

## Algorithms, grading, and similarity

DFS/BFS/IDDFS/backtracking checks use Python AST structural clues and source line references. A comment, function name, or variable name alone is not evidence. Even a matching structure is not proof of the executed algorithm: reports label it as static evidence and require human verification. Other programming languages are not analyzed. A valid output is reported independently from algorithm compliance.

Configure criteria under `rubric.criteria` only when instructor-approved. Criteria use `id`, `max_points`, `task_id`, `awards` mapping `pass`/`fail`/`manual_review` to configured scores, and optional `basis: algorithm_compliance`. Algorithm compliance always remains manual review because static analysis cannot prove behavior. No official weights are included in the default spec.

Similarity compares only repositories included in the same CLI run, with exact file hashes, normalized whole files, and normalized matching four-line fragments. Reports include paths/line starts and commit identifiers. Common starter code can match, and similarity is not an accusation or automatic grade penalty.

## GitHub

Use a least-privilege read-only `GITHUB_TOKEN` environment variable. Explicit repository scope is preferred:

```powershell
$env:GITHUB_TOKEN = 'your-read-only-token'
ai-reviewer review-github --repo course/student-one --repo course/student-two --task all --out reports
```

Alternatively configure `repositories: ["course/student-one"]` in the assignment YAML, or use `--org ORG` / `--account USER` for discovery. Private repositories need appropriate read access. GitHub list pagination, API timeouts/retries, commit SHA pinning, and error handling are implemented. The current test suite mocks pagination and snapshot retrieval; **live GitHub access has not been tested**. Downloaded content is not cached.

`scc` metrics are collected for local repositories when the `scc` executable is installed; otherwise the report records that it is unavailable. SCC output is supporting evidence only. Git history is summarized separately and commit counts/messages are not treated as quality measures.

## Configurable reviewer and optional AI interpretation

`config/reviewer.yaml` defines the reviewer role, skills, rules, workflow, evidence requirements, Definition of Done, and the default-disabled LLM settings. `rubrics/assignment-01-framework.yaml` is a qualitative template for the four tasks. It is explicitly unapproved and every weight is unset; it does not enable numeric grading. The assignment's active rubric also remains provisional unless an instructor configures and approves it.

Deterministic review works without a model or API key. To request optional qualitative interpretation, set an OpenAI-compatible Chat Completions endpoint and model, enable `llm.enabled` in a copied reviewer config, then pass `--reviewer-config` and `--ai-review`. For a local compatible endpoint, no API key is needed when the hostname is `localhost`, `127.0.0.1`, or `::1`:

```powershell
$env:AI_REVIEW_BASE_URL = 'http://localhost:1234/v1'
$env:AI_REVIEW_MODEL = 'your-local-model-id'
ai-reviewer review-local C:\submissions\student-one --task all --out reports --reviewer-config C:\config\reviewer-with-ai.yaml --ai-review
```

For an authenticated compatible hosted endpoint, also set `AI_REVIEW_API_KEY` in the environment. Never place a key in a config or command line. The application does not assume the Codex model is available to the CLI. AI output is schema checked, kept separate from deterministic findings, cannot add a score, and must cite repository files; cited paths and line ranges are checked. Repository contents are treated as untrusted evidence in the prompt.

Source upload has two independent opt-ins: set `llm.allow_source_upload: true` in the reviewer config and pass `--allow-source-upload` alongside `--ai-review`. Without both, source excerpts are omitted. Sensitive-looking filenames are excluded, common secret patterns are redacted, and the configured source character cap applies. Other collected evidence (assignment, deterministic findings, repository metadata and safe file paths) is still sent when AI review is requested. Review provider calls are not covered by the mocked tests against a live service; live model integration has not been verified. The ordinary deterministic workflow sends nothing to a model.

## Tests and fixtures

The test suite includes ordinary synthetic submission directories under `tests/fixtures/` for conventional outputs, misleading algorithm claims, incomplete evidence, and invalid transitions. Other tests cover valid/invalid task outputs, all four task reports, workforce-configured checks, static algorithm clues, rubric behavior, similarity, CLI operation, mocked GitHub integration, and mocked OpenAI-compatible request/response validation.

```powershell
python -m pytest -q
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m reviewer.cli --help
python -m reviewer.cli review-local C:\path\to\submission --task all --out reports
```

The first three tasks validate output artifacts rather than execute student solvers. Social Golfers validation checks schedule validity, not optimality or a maximum-weeks proof. Search-tree diagrams, written problem formulations, code in languages other than Python, and algorithm runtime behavior remain instructor review items. GitHub content caching and robust AST/token analysis remain future work.
