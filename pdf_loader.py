import re
from datetime import datetime, timezone
from typing import List, Optional
from pypdf import PdfReader
from schemas import BankDocument, DocumentMeta, Transaction
from config import settings

# Optional LLM (used only to refine metadata / ambiguous fields)
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

# ----- Utility parsing helpers -----
DATE_PATTERNS = [
    r"\b(\d{4})-(\d{2})-(\d{2})\b",
    r"\b(\d{2})/(\d{2})/(\d{4})\b",
    r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\b"
]
MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], start=1)}

def _norm_date(text: str) -> Optional[datetime]:
    text = text.strip()
    # ISO yyyy-mm-dd
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
    # dd/mm/yyyy
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", text)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
    # Mon dd yyyy
    m = re.match(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})$", text)
    if m:
        mon = MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return datetime(int(m.group(3)), mon, int(m.group(2)), tzinfo=timezone.utc)
    return None

def _extract_text_and_meta(pdf_path: str):
    reader = PdfReader(pdf_path)
    meta = getattr(reader, "metadata", {}) or {}
    encrypted = bool(getattr(reader, "is_encrypted", False))
    text_pages = []
    for p in reader.pages:
        try:
            text_pages.append(p.extract_text() or "")
        except Exception:
            text_pages.append("")
    return "\n".join(text_pages), meta, encrypted

def _find_account_number(text: str) -> Optional[str]:
    # Look for something labeled Account or Acct
    m = re.search(r"(?:Account|Acct)[^\d]{0,10}(\d{6,20})", text, re.IGNORECASE)
    return m.group(1) if m else None

def _find_balances(text: str):
    # Opening / Closing balance heuristics
    opening = None
    closing = None
    m = re.search(r"Opening\s+Balance[:\s]+(-?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if m: opening = float(m.group(1))
    m = re.search(r"Closing\s+Balance[:\s]+(-?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if m: closing = float(m.group(1))
    return opening, closing

def _find_period(text: str):
    # e.g. Period: 2025-08-01 to 2025-08-31
    m = re.search(r"Period[:\s]+(.+?)\bto\b(.+)", text, re.IGNORECASE)
    if m:
        start = _norm_date(m.group(1).strip())
        end_candidate = m.group(2).splitlines()[0].strip()
        end = _norm_date(end_candidate)
        return start, end
    return None, None

def _guess_document_type(text: str) -> str:
    if re.search(r"credit statement", text, re.IGNORECASE):
        return "Credit Statement"
    if re.search(r"account statement", text, re.IGNORECASE):
        return "Account Statement"
    return "Statement"

TRANSACTION_LINE_REGEX = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\s+"
    r"(?P<type>debit|credit)\s+"
    r"(?P<amount>-?\d+(?:\.\d+)?)\s+"
    r"(?P<desc>.+)$",
    re.IGNORECASE
)

def _parse_transactions(text: str) -> List[Transaction]:
    txs: List[Transaction] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 10:
            continue
        m = TRANSACTION_LINE_REGEX.match(line)
        if not m:
            continue
        dt = _norm_date(m.group("date"))
        if not dt:
            continue
        ttype = m.group("type").lower()
        amount = float(m.group("amount"))
        desc = m.group("desc").strip()
        txs.append(Transaction(
            id=f"TX{len(txs)+1}",
            timestamp=dt,
            amount=amount,
            type=ttype,
            description=desc,
            channel=""  # unknown unless inferred
        ))
    return txs

def _llm_refine(meta: DocumentMeta, raw_text: str) -> DocumentMeta:
    if not (settings.enable_llm and settings.groq_api_key and ChatGroq):
        return meta
    prompt = f"""
You are extracting normalized fields from a bank statement text.
Return JSON with keys: document_type, reported_opening_balance, reported_closing_balance.
Text:
\"\"\"{raw_text[:6000]}\"\"\"
If a value is absent, use null.
"""
    llm = ChatGroq(model=settings.llm_model, temperature=0)
    resp = llm.invoke(prompt)
    content = getattr(resp, "content", str(resp))
    import json, re
    snippet = re.search(r"\{.*\}", content, re.DOTALL)
    if snippet:
        try:
            data = json.loads(snippet.group(0))
            if data.get("document_type"):
                meta.document_type = data["document_type"]
            if data.get("reported_opening_balance") is not None:
                meta.reported_opening_balance = float(data["reported_opening_balance"])
            if data.get("reported_closing_balance") is not None:
                meta.reported_closing_balance = float(data["reported_closing_balance"])
        except Exception:
            pass
    return meta

def parse_pdf_to_bank_document(pdf_path: str, doc_id: Optional[str] = None) -> BankDocument:
    raw_text, pdf_meta, encrypted = _extract_text_and_meta(pdf_path)
    doc_id = doc_id or f"PDF_{abs(hash(pdf_path))}"
    account = _find_account_number(raw_text)
    opening, closing = _find_balances(raw_text)
    period_start, period_end = _find_period(raw_text)
    doc_type = _guess_document_type(raw_text)
    txs = _parse_transactions(raw_text)

    meta = DocumentMeta(
        document_id=doc_id,
        document_type=doc_type,
        period_start=period_start,
        period_end=period_end,
        reported_opening_balance=opening,
        reported_closing_balance=closing,
        generated_timestamp=None,
        pdf_author=pdf_meta.get("/Author"),
        pdf_creator=pdf_meta.get("/Creator"),
        pdf_producer=pdf_meta.get("/Producer"),
        pdf_encrypted=encrypted
    )

    meta = _llm_refine(meta, raw_text)

    return BankDocument(
        meta=meta,
        account_number=account,
        customer_id=None,
        institution=None,
        transactions=txs,
        raw_text=raw_text,
        source="pdf"
    )
