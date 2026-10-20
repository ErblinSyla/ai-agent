# Getting started: AI University Project Reviewer

This guide uses PowerShell on Windows. The reviewer stays in this existing repository. Your Assignment 1 student project is a separate folder and separate GitHub repository that you create yourself. Run reviewer commands from the reviewer project root so its default YAML files can be found.

## 1. Check Python and install the reviewer

Open PowerShell and go to this project:

```powershell
Set-Location 'C:\Users\erbli\OneDrive\Desktop\ai-agent'
python --version
Test-Path .venv\Scripts\python.exe
```

Python 3.11 or later is required. Reuse `.venv` if it already exists; otherwise create it. These commands do not rely on shell activation:

```powershell
if (-not (Test-Path .venv\Scripts\python.exe)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
```

The project runtime dependency is PyYAML. The `test` extra installs pytest. No LLM SDK is required; the optional provider uses Python's standard-library HTTP client. Check the install and CLI:

```powershell
.\.venv\Scripts\python.exe -m pip show PyYAML pytest
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\ai-reviewer.exe --help
.\.venv\Scripts\ai-reviewer.exe review-local --help
.\.venv\Scripts\ai-reviewer.exe review-github --help
```

The CLI itself also works before installation with `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` and `python -m reviewer.cli ...`.

## 2. What works without an LLM key

All deterministic functionality is available without Groq, OpenAI, or any other model key. The reviewer reads files without executing student code, checks supported outputs, gathers metadata/history, performs conservative Python AST checks, optionally uses `scc` if installed, compares repositories supplied in one run, and writes Markdown and JSON reports. The default config `config/reviewer.yaml` has `llm.enabled: false`; do not pass `--ai-review` for a deterministic-only review. No official grading weights are configured, and similarity is never a plagiarism verdict.

## 3. Create your separate Assignment 1 repository

The following is an example you run yourself after you have prepared the assignment folder and its contents. Replace the placeholder path. Do not create it inside this reviewer repository. Inspect the files and ensure secrets/generated files are excluded before staging:

```powershell
Set-Location 'C:\path\to\your\assignment-01'
git init -b main
git status
git add .
git status
git commit -m 'Prepare Assignment 1 submission'
```

If everything shown by `git status` belongs in the student submission, `git add .` is convenient; otherwise stage only your intended paths. After `git add`, inspect `git status` again before committing. Make sure `.env`, API keys, virtual environments, generated caches, and unrelated private files are excluded. Create an empty GitHub repository yourself using the GitHub website (do not initialize it with another README/license if you already committed those locally), then connect and push:

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_ASSIGNMENT_REPO.git
git push -u origin main
```

Replace `YOUR_ACCOUNT` and `YOUR_ASSIGNMENT_REPO`. For SSH, use your own SSH remote URL instead. You can review locally before creating or pushing to GitHub.

## 4. Prepare evidence for the supported assignment tasks

Add ordinary source, tests, and written explanations for the actual assignment. Output files help the deterministic validators; they are evidence fixtures and do not replace the required solver implementation, tests, or mathematical explanations.

- **Social Golfers:** document the state/model, variables, domains, constraints, objective, search-space derivation, DFS/backtracking approach, and tests. Supply a schedule as `social_golfers.json` or a top-level Python literal such as `SOCIAL_GOLFERS_SCHEDULE` in a social/golf-named `.py` file. JSON fields can be `n`, `groups`, `group_size`, `weeks`, and `schedule`; schedule is weeks → groups → golfer IDs. The validator checks each week's coverage/group size and repeated pairs. It does not prove maximum feasible weeks or optimality.
- **Sudoku:** document representation, domains, row/column/box constraints, search approach, tests, and support for Easy/Medium/Hard. Use `sudoku.json` with `clues` and `solution`, or paired CSV/TXT files named with `sudoku` and `clues`/`puzzle` or `solution`; matrices have one comma- or whitespace-separated row per line. For explicit difficulty fixtures use names such as `easy_sudoku_clues.csv` and `easy_sudoku_solution.csv`, likewise `medium` and `hard`, or JSON `fixtures`. A single valid puzzle is checked, but does not establish all three difficulty levels. CSV/TXT Sudoku matrices use the default 9x9/3x3-box format.
- **Latin Square:** document the variables, domains, row/column constraints, objective/search-space interpretation, IDDFS/backtracking, termination/depth behavior, tests, and multiple `n` values. Use `latin_square.json` with `board` (and optional `n`), a Latin-named CSV/TXT matrix, or a top-level literal `LATIN_SQUARE`/`LATIN_BOARD` in Python. The checker validates the supplied square, not the implementation's behavior.
- **8-Puzzle:** provide an explanation or diagram plus a structured JSON tree in `eight_puzzle.json` (or under `eight_puzzle` in `search_trees.json`). The object has `initial`, `goal`, `states`, and `edges`; each edge is `{ "from": state, "to": state, "action": label }`. States are flat lists of nine values or 3x3 lists and must be permutations of 0–8. Transitions must swap the blank with one adjacent tile. The default goal is `[1,2,3,4,5,6,7,8,0]`; document requirements that are not represented by this format.
- **Missionaries and Cannibals:** include a diagram/explanation and JSON in `missionaries_cannibals.json` (or in `search_trees.json`). Use `initial`, `goal`, `states`, and `edges`; states are `[missionaries_left, cannibals_left, boat_side]`, with boat side 0=left and 1=right. Default population is three, boat capacity is two. The validator checks bounds, bank safety, direction/capacity, and reachability through supplied edges. It does not grade an executable solver.
- **Rotating Workforce Scheduling:** document the state, initial/goal states, transitions/actions, and the instructor-provided or assignment-defined rules. Supply the same JSON tree shape in `rotating_workforce.json` or `search_trees.json`. The validator can check configured `required_state_fields`, `allowed_actions`, and `goal_reachable` under that problem's `validation_rules`. No workforce rules are assumed by default; without configured rules, some requirements stay for manual review.

Search-tree diagrams, written mathematical derivations, objective functions, test execution, and many deliverables are not automatically understood. Keep those explanations in the README or separate documents and expect an instructor to inspect them.

## 5. What the reviewer reads and what it cannot prove

The extractor reads JSON (task-keyed data, root `outputs`, named task files, or individual tree files), Python top-level literal constants parsed with `ast.literal_eval`, and the CSV/TXT matrix cases above. `review-evidence.json` is an optional convenience file; it is not required. Executable Python functions are not run to get their return values.

Algorithm analysis examines Python AST structure for DFS, BFS, IDDFS, and backtracking evidence. Names/comments alone are not enough, but a detected structure is still only a static clue: it may be unrelated to the selected task and cannot establish runtime behavior. Other languages are not analyzed. Output validity and algorithm evidence are reported separately. Files over 1 MB, undecodable binary files, symlinks, and common generated/dependency directories are skipped by local ingestion. Git history is contextual evidence. `scc` is optional; absence is recorded in the report.

The default assignment has no approved rubric, so the report is ungraded. No numeric score, plagiarism conclusion, or hidden constraint is inferred. GitHub and hosted-LLM support have test coverage with mocks only; live services require your credentials and a manual run.

## 6. Review the separate local submission

Return to the reviewer root. Substitute your actual student-repository folder and a unique report folder. The report path must stay outside the student submission:

```powershell
Set-Location 'C:\Users\erbli\OneDrive\Desktop\ai-agent'
.\.venv\Scripts\ai-reviewer.exe review-local 'C:\path\to\your\assignment-01' --task all --out '.\reports\assignment-01-student'
```

Available tasks: `all`, `social_golfers`, `sudoku`, `latin_square`, and `search_trees`. Other useful options are `--assignment PATH`, `--reviewer-config PATH`, `--ai-review`, and `--allow-source-upload`. Run `review-local --help` for the installed CLI syntax. For repeat runs, the same report filenames are overwritten. If the app says the output is inside the submission, choose a report folder elsewhere.

## 7. Read, correct, and rerun

Open `reports\assignment-01-student\assignment-01.json` for the complete structured report and `assignment-01.md` for the readable overview. Check each task's output status, `output_validation`, `algorithm_compliance`, evidence paths/lines, manual-review notes, `ai_review` if requested, rubric assessment, similarity report (when present), code metrics, and limitations. `validated output` means the supplied artifact met that validator; it is not proof that a solver produced it or used the required algorithm. Use the findings to correct the student project yourself, rerun the student's own tests, commit changes as desired, then rerun the same `review-local` command. The reviewer does not modify the submission.

## 8. Optional Groq free-tier AI interpretation

Groq documents an OpenAI-compatible endpoint at `https://api.groq.com/openai/v1`; its current model docs list `openai/gpt-oss-20b`, and its Structured Outputs docs list that model as supporting both strict and best-effort structured output. The application currently uses Chat Completions `response_format: {"type":"json_object"}` (JSON Object Mode), then independently checks its own response shape and citations. Groq documents JSON Object Mode as the fallback for models supporting Structured Outputs. Thus this request shape is compatible according to the current docs; a live call still needs your account/key and is not claimed tested here. Model identifiers can change: confirm `openai/gpt-oss-20b` on the current [models page](https://console.groq.com/docs/models) or in your dashboard before use. See also Groq's [OpenAI compatibility](https://console.groq.com/docs/openai) and [Structured Outputs](https://console.groq.com/docs/structured-outputs) docs.

1. Create/sign in to a GroqCloud account at [console.groq.com](https://console.groq.com/), open the API keys section, and create a key for this local use. A free API tier is quota-limited; free access and model limits are governed by the account/org and may change.
2. Copy the default reviewer config and edit the copy. It contains no credential. Set only `llm.enabled: true` and `llm.api_key_env: GROQ_API_KEY`; keep `llm.allow_source_upload: false`:

   ```powershell
   Copy-Item config\reviewer.yaml config\reviewer-groq.local.yaml
   notepad config\reviewer-groq.local.yaml
   ```

3. Set the key for this PowerShell session without putting its characters in a command or echoing it. The secure prompt is hidden; the key is then held in the process environment for the provider request:

   ```powershell
   $secureKey = Read-Host 'Groq API key' -AsSecureString
   $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
   try { $env:GROQ_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer) }
   finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer); Remove-Variable secureKey, keyPointer }
   $env:AI_REVIEW_BASE_URL = 'https://api.groq.com/openai/v1'
   $env:AI_REVIEW_MODEL = 'openai/gpt-oss-20b'
   ```

   The YAML setting `api_key_env: GROQ_API_KEY` tells this application which environment variable to read. Base URL and model use the existing `AI_REVIEW_BASE_URL` and `AI_REVIEW_MODEL` names. Do not put the key in YAML, `.env`, a script, or the Git repository. The config copy is ignored by this project's `.gitignore` when named `config/reviewer-groq.local.yaml`.

   The repository's `.env.example` is only a list of variable names and is not automatically loaded by Python; set variables in the current PowerShell session as shown.

4. Optional: confirm the selected model is currently listed without displaying your key:

   ```powershell
   (Invoke-RestMethod -Uri 'https://api.groq.com/openai/v1/models' -Headers @{ Authorization = "Bearer $env:GROQ_API_KEY" }).data.id
   ```

5. Request a qualitative review without sending source excerpts:

   ```powershell
   .\.venv\Scripts\ai-reviewer.exe review-local 'C:\path\to\your\assignment-01' --task all --out '.\reports\assignment-01-ai' --reviewer-config '.\config\reviewer-groq.local.yaml' --ai-review
   ```

   Check `ai_review.status` in the JSON report; it should be `completed` after a successful live request. The Markdown report always has an “Optional AI interpretation” section that displays its status. With source upload disabled, the model still receives assignment configuration, deterministic findings/output validation, repository name/commit, and non-sensitive repository-relative file paths; it does not receive source excerpts. A hosted provider receives that submitted context, so review only repositories/data you are authorized to share.

   If you later decide source excerpts may be shared with Groq, read its current [data handling documentation](https://console.groq.com/docs/your-data), terms, and your university's student-data policy first. Groq currently says inference data is not retained by default, but inputs/outputs may be temporarily retained for reliability or abuse investigations for up to 30 days unless Zero Data Retention is enabled in account controls. Then change `llm.allow_source_upload: true` in the local config copy and add `--allow-source-upload` to the command. **Both switches are required**; neither is enabled by default. Excerpts are capped and common secret patterns/sensitive-looking filenames are filtered, but filtering is not a guarantee that all confidential data is removed. Keep upload disabled when uncertain. Clear the session key afterward with `Remove-Item Env:GROQ_API_KEY`.

The free tier is rate-limited by request and token windows (RPM, RPD, TPM, and TPD), applied at the organization level. The current published free-plan table lists `openai/gpt-oss-20b` at 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD; these values and which models are free can change, and your Groq account's limits page is authoritative. Free access is restricted to the currently designated free-plan models/quotas; check the [rate-limits documentation](https://console.groq.com/docs/rate-limits) before each course run. HTTP `401` usually means a missing/invalid key or a wrong key environment variable. HTTP `429` means a rate/quota limit; wait for the documented reset or continue with deterministic review (omit `--ai-review`). HTTP `400` usually points to an invalid/retired model ID or rejected request/response format; verify the model ID and that it supports JSON output. See Groq's [error code guide](https://console.groq.com/docs/errors). The report records the AI call as unavailable/failed while deterministic findings remain in the report. ChatGPT Plus/Codex access does not supply a Groq or other provider API key or credits.

## 9. Review the GitHub submission

First ensure local review works. For a public repository, no token is required. For a private repository, create a fine-grained GitHub personal access token scoped to only the selected repository, with repository **Contents: read-only**; Metadata read access is used for repository metadata. Do not grant write access. GitHub organization policy may require token approval. The API is read-only, but the reviewer downloads repository contents into process memory for analysis. GitHub's official [token permissions docs](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens) and [PAT setup guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) describe scope/permissions.

Set a private-repository token in the current session using a hidden prompt (same secure environment-variable technique as above, replacing the variable with `$env:GITHUB_TOKEN`), then run one explicit repository:

```powershell
.\.venv\Scripts\ai-reviewer.exe review-github --repo YOUR_ACCOUNT/YOUR_ASSIGNMENT_REPO --task all --out '.\reports\github-assignment-01'
```

Or review several specified repositories by repeating `--repo`. CLI-supported discovery options are `--org ORGANIZATION` and `--account USER`; alternatively `repositories` can be configured in the assignment YAML. For example:

```powershell
.\.venv\Scripts\ai-reviewer.exe review-github --org YOUR_ORG --task all --out '.\reports\github-org-review'
```

To use the optional AI with GitHub, add the same config/AI flags as for local review. Keep source upload off unless you have authorization to send those source excerpts to the hosted provider. Delete the session token after use with `Remove-Item Env:GITHUB_TOKEN`. No GitHub endpoint writes are made. Live GitHub retrieval has only mock test coverage in this workspace.

## Troubleshooting

- **`python` not found or too old:** install Python 3.11+, reopen PowerShell, and verify `python --version`. `py -0p` lists installed Windows Python interpreters.
- **Virtual environment activation policy:** activation is optional; use the explicit `.\.venv\Scripts\python.exe` and `ai-reviewer.exe` paths shown here. If you choose activation, follow your local PowerShell policy rather than changing machine-wide policy.
- **`No module named reviewer`:** reinstall with `python -m pip install -e '.[test]'` from this project's root, or set `PYTHONPATH` to this project's `src` directory.
- **PyYAML/config errors:** run the CLI from the reviewer root, check `assignments/2026-27/assignment-01.yaml` and `config/reviewer.yaml` exist, and validate any edited YAML indentation. Pass alternate files explicitly with `--assignment PATH` / `--reviewer-config PATH`.
- **No task output / manual review:** check filenames, JSON task IDs/keys, matrix shape, Python literal constant names, and supported formats above. A function result is not evaluated. Unsupported language code and diagrams need human review.
- **GitHub 404/401/403/429:** verify `OWNER/REPO`, repository visibility, token expiry/resource-owner/repository selection, `Contents: read-only`, and organization approval. Public repositories may be reviewed without a token. A 403/429 can indicate rate limits or access restrictions; wait/check GitHub status and token scope, then retry. GitHub failures are printed as skips; if no repo was retrieved, the CLI exits with an error. The live API path has mock tests only, and large/truncated GitHub trees are not specially handled, so verify retrieved file counts for unusually large repositories.
- **Groq 401/429/400:** check the secure key session variable and `api_key_env`, wait/review quota on 429, and confirm the current model ID/JSON-object support on 400. The app does not print the key and the deterministic path remains available without `--ai-review`.
- **AI says unavailable/failed:** open the JSON report's `ai_review.error`; the deterministic findings should still be present. Check that AI is enabled only in the chosen reviewer config and that the base URL/model variables are set. A live request cannot be confirmed without your credentials and network access.
- **Output path rejected:** move `--out` to any folder outside the local student repository.
