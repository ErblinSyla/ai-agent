"""Validate the public report contract used by the class demonstration."""

import argparse
import json
from pathlib import Path

_AI_FINDING_FIELDS = {
    "task_id", "category", "observations", "assessment", "confidence",
    "uncertainties", "evidence", "recommendation",
}
_AI_CATEGORIES = {
    "requirement_compliance", "problem_formulation", "algorithm_evidence", "correctness",
    "complexity", "testing", "code_quality", "similarity_context", "general",
}


def report_errors(report):
    """Return report-contract errors without assuming an AI result exists."""
    errors = []
    if not isinstance(report, dict):
        return ["report root must be a JSON object"]

    findings = report.get("findings")
    if not isinstance(findings, list) or not findings:
        errors.append("deterministic findings must be a non-empty list")

    ai = report.get("ai_review")
    if not isinstance(ai, dict):
        return errors + ["ai_review must be an object"]
    if ai.get("status") != "completed":
        errors.append(f"ai_review.status must be 'completed' (got {ai.get('status')!r})")
        return errors
    if ai.get("source_code_sent") is not False:
        errors.append("ai_review.source_code_sent must be false")

    result = ai.get("result")
    if not isinstance(result, dict):
        errors.append("ai_review.result must be an object")
        return errors
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
        errors.append("ai_review.result.summary must be a non-empty string")
    if set(result) != {"summary", "findings"}:
        errors.append("ai_review.result must contain only summary and findings")
    ai_findings = result.get("findings")
    if not isinstance(ai_findings, list):
        errors.append("ai_review.result.findings must be a list")
    elif len(ai_findings) > 30:
        errors.append("ai_review.result.findings exceeds the schema limit of 30")
    else:
        for index, finding in enumerate(ai_findings):
            prefix = f"ai_review.result.findings[{index}]"
            if not isinstance(finding, dict):
                errors.append(f"{prefix} must be an object")
                continue
            missing = sorted(_AI_FINDING_FIELDS - finding.keys())
            if missing:
                errors.append(f"{prefix} is missing required fields: {', '.join(missing)}")
                continue
            if finding.keys() - _AI_FINDING_FIELDS:
                errors.append(f"{prefix} contains fields outside the response schema")
            if not isinstance(finding["task_id"], str) or not finding["task_id"].strip():
                errors.append(f"{prefix}.task_id must be a non-empty string")
            if not isinstance(finding["assessment"], str) or not finding["assessment"].strip():
                errors.append(f"{prefix}.assessment must be a string")
            if not isinstance(finding["category"], str) or finding["category"] not in _AI_CATEGORIES:
                errors.append(f"{prefix}.category is outside the response schema")
            if (not isinstance(finding["observations"], list)
                    or len(finding["observations"]) > 10
                    or not all(isinstance(item, str) for item in finding["observations"])
                    or not isinstance(finding["uncertainties"], list)
                    or len(finding["uncertainties"]) > 10
                    or not all(isinstance(item, str) for item in finding["uncertainties"])):
                errors.append(f"{prefix}.observations and uncertainties must be lists of strings")
            evidence = finding["evidence"]
            if not isinstance(evidence, list) or len(evidence) > 20:
                errors.append(f"{prefix}.evidence must be a list")
            else:
                for evidence_index, item in enumerate(evidence):
                    bounds_ok = isinstance(item, dict) and set(item) == {"path", "line_start", "line_end"} and all(
                        key in item and (item[key] is None or (type(item[key]) is int and item[key] >= 1))
                        for key in ("line_start", "line_end")
                    )
                    if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item.get("path", "").strip() or not bounds_ok:
                        errors.append(f"{prefix}.evidence[{evidence_index}] has an invalid citation shape")
                    elif ((item["line_start"] is None) != (item["line_end"] is None)
                          or (item["line_start"] is not None and item["line_start"] > item["line_end"])):
                        errors.append(f"{prefix}.evidence[{evidence_index}] has invalid line bounds")
            if not isinstance(finding["recommendation"], str) or not finding["recommendation"].strip():
                errors.append(f"{prefix}.recommendation must be a non-empty string")
            if not isinstance(finding["confidence"], str) or finding["confidence"] not in {"low", "medium", "high"}:
                errors.append(f"{prefix}.confidence must be low, medium, or high")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify a saved AI reviewer report for the class demo")
    parser.add_argument("report", help="path to the report JSON")
    args = parser.parse_args(argv)
    path = Path(args.report)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read valid JSON report at {path}: {exc}")
        return 1
    errors = report_errors(report)
    if errors:
        print(f"FAIL: {path}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {path}")
    print(f"AI summary: {report['ai_review']['result']['summary'].strip()}")
    print(f"Deterministic findings: {len(report['findings'])}; AI findings: {len(report['ai_review']['result']['findings'])}")
    print("Source code sent: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
