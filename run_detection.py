import json
import argparse
from datetime import datetime, timezone
from schemas import BankDocument, DocumentMeta, Transaction
from graph import run_pipeline
from report import generate_markdown_report  # added
from pdf_loader import parse_pdf_to_bank_document  # NEW

def sample_document() -> BankDocument:
    txs = [
        Transaction(id="T1", timestamp=datetime(2025,9,1,10,0,tzinfo=timezone.utc), amount=500.0, type="credit", description="Salary"),
        Transaction(id="T2", timestamp=datetime(2025,9,2,9,0,tzinfo=timezone.utc), amount=200.0, type="debit", description="ATM withdrawal"),
        Transaction(id="T3", timestamp=datetime(2025,9,2,9,0,tzinfo=timezone.utc), amount=200.0, type="debit", description="Duplicate timestamp"),
        Transaction(id="T4", timestamp=datetime(2025,9,30,20,0,tzinfo=timezone.utc), amount=9999.0, type="debit", description="Manual Override adjustment"),
    ]
    meta = DocumentMeta(
        document_id="DOC123",
        document_type="Credit Statement",
        period_start=datetime(2025,9,1,tzinfo=timezone.utc),
        period_end=datetime(2025,9,30,tzinfo=timezone.utc),
        reported_opening_balance=1000.0,
        reported_closing_balance=300.0,  # intentionally mismatched
        generated_timestamp=datetime(2025,10,1,12,0,tzinfo=timezone.utc)
    )
    raw_text = """
    STATEMENT OF ACCOUNT
    Account: 123456789
    Date Range: Sep 01 - Sep 30 2025
    Manual Override applied
    """
    return BankDocument(
        meta=meta,
        account_number="123456789",
        customer_id="CUST55",
        institution="BankCorp",
        transactions=txs,
        raw_text=raw_text
    )

def load_document_from_json(path: str) -> BankDocument:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BankDocument.parse_obj(data)

def print_result(result):
    print("Document ID:", result.document_id)
    print("Classification:", result.classification)
    print(f"Base Risk: {result.base_risk_score:.2f}")
    if result.llm_risk_score is not None:
        print(f"LLM Risk Adj: {result.llm_risk_score:.2f}")
    print(f"Combined Risk: {result.combined_risk_score:.2f}")
    print("Issues:")
    if not result.issues:
        print("  (none)")
    for i in result.issues:
        print(f" - {i.code} [{i.severity}] {i.message} (impact {i.score_impact})")
    if result.llm_reasoning:
        print("\nLLM Reasoning:\n", result.llm_reasoning)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", help="Path to sample JSON document.")
    parser.add_argument("--pdf", help="Path to a text-based PDF statement.")
    parser.add_argument("--report", "-r", help="Path to write markdown report.")
    args = parser.parse_args()

    if args.pdf:
        doc = parse_pdf_to_bank_document(args.pdf)
    elif args.file:
        doc = load_document_from_json(args.file)
    else:
        doc = sample_document()

    result = run_pipeline(doc)
    print_result(result)

    if args.report:
        out = generate_markdown_report(result, args.report)
        print(f"\nReport written: {out}")

if __name__ == "__main__":
    main()
