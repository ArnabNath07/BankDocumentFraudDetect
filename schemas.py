from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Transaction(BaseModel):
    id: str
    timestamp: datetime
    amount: float
    currency: str = "USD"
    type: str  # "debit" | "credit"
    description: Optional[str] = ""
    channel: Optional[str] = ""  # e.g., "ATM", "ONLINE"

class DocumentMeta(BaseModel):
    document_id: str
    document_type: str  # e.g., "Credit Statement", "Account Statement"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_timestamp: Optional[datetime] = None
    reported_opening_balance: Optional[float] = None
    reported_closing_balance: Optional[float] = None
    # --- PDF specific metadata (optional) ---
    pdf_author: Optional[str] = None
    pdf_creator: Optional[str] = None
    pdf_producer: Optional[str] = None
    pdf_encrypted: Optional[bool] = None

class BankDocument(BaseModel):
    meta: DocumentMeta
    account_number: Optional[str]
    customer_id: Optional[str]
    institution: Optional[str]
    transactions: List[Transaction] = Field(default_factory=list)
    raw_text: Optional[str] = None
    source: Optional[str] = None
    # --- newly added optional extracted fields ---
    ifsc_code: Optional[str] = None
    branch: Optional[str] = None

class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: str  # INFO | WARN | ERROR
    score_impact: float = 0.0

class DetectionResult(BaseModel):
    document_id: str
    base_risk_score: float
    llm_risk_score: Optional[float]
    combined_risk_score: float
    issues: List[ValidationIssue]
    llm_reasoning: Optional[str]
    classification: str  # VALID | SUSPICIOUS | FRAUD_LIKELY
