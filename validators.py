from typing import List
from schemas import BankDocument, ValidationIssue
from dateutil import parser
from pdf_checks import pdf_specific_validator  # added
import re  # added

def missing_fields_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    # account_number & customer_id handled by identity enrichment validator now
    required = ["transactions"]
    for f in required:
        if getattr(doc, f) in (None, "", []) :
            issues.append(ValidationIssue(
                code="MISSING_FIELD",
                message=f"Missing required field: {f}",
                severity="ERROR",
                score_impact=8.0
            ))
    return issues

# --- NEW: identity + banking details enrichment/validation ---
ACCOUNT_REGEX = re.compile(r'(?:Account\s+(?:Number|No\.?))[:\s]*([A-Z0-9\-]{6,})', re.IGNORECASE)
CUSTOMER_REGEX = re.compile(r'(?:Customer\s*ID|Customer\s*No\.?|CIF\s*ID|CIF\s*No\.?)[:\s]*([A-Z0-9\-]{3,})', re.IGNORECASE)
IFSC_REGEX = re.compile(r'\b([A-Z]{4}0[0-9A-Z]{6})\b')
BRANCH_REGEX = re.compile(r'Branch(?:\s+Name)?[:\s]+([A-Za-z0-9 ,.\-&]{3,50})', re.IGNORECASE)

def identity_enrichment_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    text = (doc.raw_text or "")
    lower = text.lower()

    # Account number
    if not doc.account_number:
        m = ACCOUNT_REGEX.search(text)
        if m:
            doc.account_number = m.group(1)
            issues.append(ValidationIssue(
                code="AUTO_FILLED_FIELD",
                message="Auto-filled account_number from text.",
                severity="INFO",
                score_impact=0.5
            ))
    if not doc.account_number:
        issues.append(ValidationIssue(
            code="MISSING_ACCOUNT_IDENTIFIER",
            message="No 'Account Number' or 'Account No.' found.",
            severity="ERROR",
            score_impact=7.0
        ))

    # Customer / CIF
    if not doc.customer_id:
        m = CUSTOMER_REGEX.search(text)
        if m:
            doc.customer_id = m.group(1)
            issues.append(ValidationIssue(
                code="AUTO_FILLED_FIELD",
                message="Auto-filled customer_id (Customer/CIF ID) from text.",
                severity="INFO",
                score_impact=0.5
            ))
    if not doc.customer_id:
        issues.append(ValidationIssue(
            code="MISSING_CUSTOMER_IDENTIFIER",
            message="No 'Customer ID' or 'CIF ID' found.",
            severity="ERROR",
            score_impact=6.0
        ))

    # IFSC
    if not getattr(doc, "ifsc_code", None):
        m = IFSC_REGEX.search(text)
        if m:
            doc.ifsc_code = m.group(1)
            issues.append(ValidationIssue(
                code="AUTO_FILLED_FIELD",
                message="Auto-filled IFSC code.",
                severity="INFO",
                score_impact=0.5
            ))
    if not getattr(doc, "ifsc_code", None):
        issues.append(ValidationIssue(
            code="MISSING_IFSC",
            message="No IFSC code detected.",
            severity="WARN",
            score_impact=3.0
        ))

    # Branch
    if not getattr(doc, "branch", None):
        m = BRANCH_REGEX.search(text)
        if m:
            doc.branch = m.group(1).strip()
            issues.append(ValidationIssue(
                code="AUTO_FILLED_FIELD",
                message="Auto-filled branch name.",
                severity="INFO",
                score_impact=0.5
            ))
    if not getattr(doc, "branch", None):
        issues.append(ValidationIssue(
            code="MISSING_BRANCH",
            message="No Branch label found.",
            severity="WARN",
            score_impact=2.0
        ))

    return issues

def mismatch_totals_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    if doc.meta.reported_opening_balance is None or doc.meta.reported_closing_balance is None:
        return issues
    total_debits = sum(t.amount for t in doc.transactions if t.type.lower() == "debit")
    total_credits = sum(t.amount for t in doc.transactions if t.type.lower() == "credit")
    computed_closing = doc.meta.reported_opening_balance + total_credits - total_debits
    if abs(computed_closing - doc.meta.reported_closing_balance) > 0.01:
        issues.append(ValidationIssue(
            code="BALANCE_MISMATCH",
            message=f"Computed closing {computed_closing:.2f} != reported {doc.meta.reported_closing_balance:.2f}",
            severity="ERROR",
            score_impact=15.0
        ))
    return issues

def document_type_consistency_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    doc_type = doc.meta.document_type.lower()
    has_only_debits = all(t.type.lower()=="debit" for t in doc.transactions) if doc.transactions else False
    if "credit" in doc_type and has_only_debits:
        issues.append(ValidationIssue(
            code="DOC_TYPE_MISMATCH",
            message="Document labeled as credit but contains only debit transactions.",
            severity="WARN",
            score_impact=6.0
        ))
    return issues

def date_irregularities_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    timestamps = [t.timestamp for t in doc.transactions]
    if not timestamps:
        return issues
    sorted_ts = sorted(timestamps)
    duplicates = len(timestamps) - len(set(timestamps))
    if duplicates > 0:
        issues.append(ValidationIssue(
            code="DUPLICATE_TIMESTAMPS",
            message=f"{duplicates} duplicate transaction timestamps detected.",
            severity="WARN",
            score_impact=5.0
        ))
    # Future dated entries
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    future = [ts for ts in timestamps if ts > now]
    if future:
        issues.append(ValidationIssue(
            code="FUTURE_DATES",
            message=f"{len(future)} future-dated transactions.",
            severity="ERROR",
            score_impact=12.0
        ))
    # Period containment
    if doc.meta.period_start and doc.meta.period_end:
        outside = [ts for ts in timestamps if not (doc.meta.period_start <= ts <= doc.meta.period_end)]
        if outside:
            issues.append(ValidationIssue(
                code="OUT_OF_PERIOD",
                message=f"{len(outside)} transactions outside stated period.",
                severity="WARN",
                score_impact=7.0
            ))
    return issues

SUSPICIOUS_KEYWORDS = ["manual override", "adjustment", "force post", "backdated"]

def suspicious_keyword_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    text = (doc.raw_text or "").lower()
    hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in text]
    if hits:
        issues.append(ValidationIssue(
            code="SUSPICIOUS_TERMS",
            message=f"Suspicious keywords present: {', '.join(hits)}",
            severity="WARN",
            score_impact=10.0
        ))
    return issues

def structural_format_validator(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    # Simple heuristics; can extend with template registry
    required_headers = ["statement", "account", "date"]
    text = (doc.raw_text or "").lower()
    missing = [h for h in required_headers if h not in text]
    if missing:
        issues.append(ValidationIssue(
            code="FORMAT_MISSING_HEADERS",
            message=f"Missing expected header tokens: {', '.join(missing)}",
            severity="WARN",
            score_impact=5.0
        ))
    return issues

ALL_VALIDATORS = [
    identity_enrichment_validator,  # added first so enrichment happens early
    missing_fields_validator,
    mismatch_totals_validator,
    document_type_consistency_validator,
    date_irregularities_validator,
    suspicious_keyword_validator,
    structural_format_validator,
    pdf_specific_validator  # (already present if earlier added)
]

def run_validators(doc: BankDocument) -> List[ValidationIssue]:
    issues = []
    for v in ALL_VALIDATORS:
        issues.extend(v(doc))
    return issues
