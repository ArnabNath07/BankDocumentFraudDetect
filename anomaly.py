from typing import List
from schemas import BankDocument, ValidationIssue
import statistics

def transaction_amount_anomalies(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    amounts = [t.amount for t in doc.transactions]
    if len(amounts) < 5:
        return issues
    mean = statistics.mean(amounts)
    stdev = statistics.pstdev(amounts)
    if stdev == 0:
        return issues
    outliers = [a for a in amounts if abs(a - mean) > 3 * stdev]
    if outliers:
        issues.append(ValidationIssue(
            code="AMOUNT_OUTLIERS",
            message=f"{len(outliers)} amount outliers vs distribution.",
            severity="WARN",
            score_impact=9.0
        ))
    return issues

def frequency_anomalies(doc: BankDocument) -> List[ValidationIssue]:
    from collections import Counter
    issues = []
    channels = [t.channel for t in doc.transactions if t.channel]
    if not channels:
        return issues
    c = Counter(channels)
    dominant, freq = c.most_common(1)[0]
    if freq / len(channels) > 0.9 and len(channels) >= 10:
        issues.append(ValidationIssue(
            code="CHANNEL_DOMINANCE",
            message=f"Single channel '{dominant}' dominates {freq}/{len(channels)}.",
            severity="INFO",
            score_impact=4.0
        ))
    return issues

ANOMALY_FUNCTIONS = [
    transaction_amount_anomalies,
    frequency_anomalies
]

def run_anomalies(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    for f in ANOMALY_FUNCTIONS:
        issues.extend(f(doc))
    return issues
