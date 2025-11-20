from pathlib import Path
from datetime import datetime, timezone
from schemas import DetectionResult

def _group_issues(issues):
    grouped = {}
    for i in issues:
        grouped.setdefault(i.severity, []).append(i)
    return grouped

def generate_markdown_report(result: DetectionResult, output_path: str):
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    grouped = _group_issues(result.issues)
    now = datetime.now(timezone.utc).isoformat()

    base_section = []
    for sev in sorted(grouped.keys()):
        base_section.append(f"### {sev} Issues ({len(grouped[sev])})")
        for issue in grouped[sev]:
            base_section.append(f"- {issue.code}: {issue.message} (impact {issue.score_impact})")
        base_section.append("")

    issues_md = "\n".join(base_section) if base_section else "No issues detected."

    llm_block = f"\n### LLM Reasoning\n{result.llm_reasoning}\n" if result.llm_reasoning else ""

    classification_flag = {
        "VALID": "✅ VALID (No significant fraud indicators)",
        "SUSPICIOUS": "⚠️ SUSPICIOUS (Further review recommended)",
        "FRAUD_LIKELY": "🚨 FRAUD LIKELY (High risk of manipulation)"
    }.get(result.classification, result.classification)

    risk_level = ("LOW" if result.combined_risk_score < 18
                  else "MEDIUM" if result.combined_risk_score < 40
                  else "HIGH")

    md = f"""# Fraud Activity Report
Generated: {now}

## Document
- Document ID: {result.document_id}
- Classification: {classification_flag}
- Risk Level: {risk_level}
- Base Risk Score: {result.base_risk_score:.2f}
- LLM Adjustment: {result.llm_risk_score or 0:.2f}
- Combined Risk Score: {result.combined_risk_score:.2f}

## Summary
This report consolidates rule-based validation and anomaly detection to assess document integrity and potential fraud signals.

## Issue Breakdown
{issues_md}
{llm_block}
## Interpretation Guide
- Base Risk: Deterministic rules (missing fields, mismatches, anomalies)
- LLM Adjustment: Contextual refinement
- Combined Risk: Base + adjustment (floored at 0)
"""

    p.write_text(md, encoding="utf-8")
    return str(p)
