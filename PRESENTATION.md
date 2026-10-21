# Professor demonstration guide

## What the reviewer does

The AI University Project Reviewer reads a submission without executing student code. It applies deterministic validators to supported output artifacts, records static Python AST clues, summarizes repository metadata, and can request a separate qualitative AI interpretation. The configured assignment contains four tasks: Social Golfers, Sudoku, Latin Square, and Search Trees (8-puzzle, missionaries and cannibals, and rotating workforce).

## Run the demonstration

From Git Bash, at any working directory:

```bash
/c/Users/erbli/OneDrive/Desktop/ai-agent/run-class-demo.sh
```

The script activates the repository `.venv`, uses its ignored `.env` and `config/reviewer-groq.local.yaml`, performs an AI review with source upload disabled, and validates the saved JSON contract. It prints the unique report path and PASS only after the actual report passes verification. If the assignment folder moves, set `AI_REVIEW_ASSIGNMENT` to its new Git Bash path before running.

The most recent demo report is the path printed by the script, normally `reports/class-demo-<timestamp>-<pid>-<random>/ai-assignment-01.json`. A verified pre-demo report is retained at `reports/final/ai-assignment-01.json`.

## What to show in the report

- Top-level `findings`: deterministic task output validation and its recorded evidence.
- `ai_review.result.summary` and `ai_review.result.findings`: optional qualitative interpretation, assessment, uncertainty, and recommendations.
- `ai_review.source_code_sent`: must be `false` for this demo configuration.
- `evaluation_mode` and `limitations`: this workflow is static and does not run the student's program.

The Markdown report also separates **Findings** from **Optional AI interpretation**. AI text is not deterministic validation and is not a proof of runtime behavior.

## Four example AI findings

The latest verified real-assignment report at `reports/final/ai-assignment-01.json` contains four illustrative AI task findings:

1. **Social Golfers:** the source-free AI review cannot confirm DFS or backtracking compliance; confidence is low.
2. **Sudoku:** the source-free AI review cannot confirm BFS or backtracking compliance; confidence is low.
3. **Latin Square:** the source-free AI review cannot confirm IDDFS or backtracking compliance; confidence is low.
4. **Search Trees:** the source-free AI review cannot confirm the search implementation; the separate deterministic result reports whether the submitted tree transitions satisfy the configured rules.

These examples are qualitative assessments generated without source excerpts. Their evidence arrays are intentionally empty, and the reviewer reports low confidence. Any recommendation to inspect code means instructor-side/local inspection; the reviewer does not upload source code. The deterministic findings retain their own file and line references.

## Honest explanation for the presentation

“This tool checks submitted structured outputs with deterministic validators and reports static clues about possible algorithms. It then asks an optional AI reviewer to interpret the resulting evidence without uploading the student's source code. It does not execute the assignment, prove algorithm compliance, or assign a grade. Any uncertain or incomplete evidence is left for the instructor to assess.”

## Troubleshooting

- Confirm `.env` and `config/reviewer-groq.local.yaml` exist; neither file's contents are printed by the demo script.
- Confirm the local config enables the provider and keeps `allow_source_upload: false`.
- If the submission moved, set `AI_REVIEW_ASSIGNMENT=/c/path/to/submission` in Git Bash.
- A `FAIL` from report verification means the saved report did not satisfy the required AI and deterministic report fields; inspect the JSON error/status without sharing credentials.
- For provider HTTP errors or rate limits, retain the request ID from the report and retry later or contact provider support. The latest successful report remains available at `reports/final/ai-assignment-01.json`.
- Tests use mocked provider calls. A live Groq result is verified only when the demo command completes with PASS.
