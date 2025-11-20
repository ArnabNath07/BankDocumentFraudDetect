import json
import tempfile
from pathlib import Path
import streamlit as st

from config import settings
from schemas import BankDocument
from graph import run_pipeline
from report import generate_markdown_report
from pdf_loader import parse_pdf_to_bank_document

st.set_page_config(page_title="Bank Statement Fraud Detector", layout="wide")

st.title("Bank Statement Fraud Detection (No OCR)")

# Sidebar controls
st.sidebar.header("Input")
uploaded_file = st.sidebar.file_uploader("Upload PDF or JSON", type=["pdf", "json"])
enable_llm = st.sidebar.checkbox("Enable LLM refinement", value=settings.enable_llm)
show_raw = st.sidebar.checkbox("Show raw extracted text", value=False)
run_btn = st.sidebar.button("Run Detection")

# Helper: load document
def load_json_bytes(b: bytes) -> BankDocument:
    data = json.loads(b.decode("utf-8"))
    return BankDocument.parse_obj(data)

def process_pdf_bytes(b: bytes, name: str) -> BankDocument:
    # Write temp file because pdf_loader expects a path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(b)
        tmp.flush()
        doc = parse_pdf_to_bank_document(tmp.name, doc_id=f"PDF_{name}")
    return doc

@st.cache_data(show_spinner=False)
def cached_run(doc: BankDocument, enable_llm_flag: bool):
    # Temporarily toggle global setting (simple approach)
    original = settings.enable_llm
    settings.enable_llm = enable_llm_flag
    result = run_pipeline(doc)
    settings.enable_llm = original
    return result

doc = None
result = None

if run_btn and uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".json"):
            doc = load_json_bytes(uploaded_file.read())
            doc.source = doc.source or "json"
        else:
            doc = process_pdf_bytes(uploaded_file.read(), uploaded_file.name)
        result = cached_run(doc, enable_llm)
    except Exception as e:
        st.error(f"Failed to process file: {e}")

if result:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Classification", result.classification)
    col2.metric("Base Risk", f"{result.base_risk_score:.2f}")
    col3.metric("LLM Adj", f"{(result.llm_risk_score or 0):.2f}")
    col4.metric("Combined", f"{result.combined_risk_score:.2f}")

    st.subheader("Issues")
    if not result.issues:
        st.success("No issues detected.")
    else:
        # Group by severity preserving insertion order
        severity_order = ["ERROR", "WARN", "INFO"]
        for sev in severity_order:
            sev_issues = [i for i in result.issues if i.severity == sev]
            if not sev_issues:
                continue
            if sev == "ERROR":
                st.markdown(f"**❌ {sev} ({len(sev_issues)})**")
            elif sev == "WARN":
                st.markdown(f"**⚠️ {sev} ({len(sev_issues)})**")
            else:
                st.markdown(f"**ℹ️ {sev} ({len(sev_issues)})**")
            for i in sev_issues:
                st.write(f"- `{i.code}` (impact {i.score_impact}) — {i.message}")

    if result.llm_reasoning:
        with st.expander("LLM Reasoning"):
            st.markdown(result.llm_reasoning)

    if show_raw and doc and doc.raw_text:
        with st.expander("Raw Extracted Text"):
            st.text(doc.raw_text[:40000])

    # Generate on-demand report (in-memory)
    from report import generate_markdown_report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / f"{result.document_id}_report.md"
    generate_markdown_report(result, str(out_path))
    md_content = out_path.read_text(encoding="utf-8")
    st.download_button(
        "Download Markdown Report",
        data=md_content,
        file_name=f"{result.document_id}_report.md",
        mime="text/markdown"
    )

else:
    st.info("Upload a PDF or JSON and click 'Run Detection'.")

st.sidebar.markdown("---")
st.sidebar.caption("Fraud Detector UI")
