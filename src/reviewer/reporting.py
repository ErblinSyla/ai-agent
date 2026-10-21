import json
from pathlib import Path

def render_markdown(report):
    lines=[f"# Review: {report['repository']}","",f"- Assignment: {report['assignment_id']} ({report['assignment_version']})",f"- Reviewed commit: `{report['commit_sha']}`",f"- Local tree digest: `{report.get('reviewed_tree_sha256', 'not available')}`",f"- Task selection: {report.get('selected_task','all')}",f"- Evaluation: {report['evaluation_mode']}",f"- Assessment: **{report.get('assessment_status','ungraded')}**",f"- Rubric: {report['rubric_version']}","", "## Repository summary",f"{json.dumps(report['repository_summary'],ensure_ascii=False)}","", "## Findings"]
    for f in report["findings"]:
        lines += [f"### {f['task']} (`{f['task_id']}`)",f"Output status: **{f['status']}**", "", "Output validation:",f"```json\n{json.dumps(f['output_validation'],indent=2,ensure_ascii=False)}\n```", "Search space / state count:", f"```json\n{json.dumps(f.get('search_space',{}),indent=2,ensure_ascii=False)}\n```", "Algorithm compliance:", f"Required: {', '.join(f['algorithm_compliance']['required']) or 'none'}", f"{f['algorithm_compliance']['summary']}", f"```json\n{json.dumps(f['algorithm_compliance']['analysis'],indent=2,ensure_ascii=False)}\n```", "Source evidence:", f"```json\n{json.dumps(f['evidence_search'],indent=2,ensure_ascii=False)}\n```", ""]
    ai=report.get("ai_review",{"status":"not requested"})
    lines += ["## Optional AI interpretation", "This qualitative interpretation is separate from deterministic findings and does not demonstrate execution or prove correctness.", f"Status: **{ai.get('status','unknown')}**"]
    if ai.get("result") is not None: lines += [f"AI summary: {ai['result']['summary']}", f"```json\n{json.dumps(ai['result']['findings'],indent=2,ensure_ascii=False)}\n```", "AI output is interpretation, not a verified deterministic result."]
    elif ai.get("error"): lines.append(f"Unavailable/error: {ai['error']}")
    lines += ["", "## Scoring"]
    if report.get("score") is None: lines.append("Ungraded: no approved configured rubric produced a score.")
    else: lines.append(f"{json.dumps(report['score'],indent=2,ensure_ascii=False)}")
    lines += ["", "## Similarity", "Compare the separate `similarity.json` report when present. Similarity is not proof of misconduct.", "", "## Code metrics", f"```json\n{json.dumps(report['code_metrics'],indent=2,ensure_ascii=False)}\n```", "", "## Limitations", *[f"- {x}" for x in report["limitations"]]]
    return "\n".join(lines)+"\n"

def write_report(report, outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); stem=report['repository'].replace('/','_')
    (out/f"{stem}.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/f"{stem}.md").write_text(render_markdown(report),encoding="utf-8")
