import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

APP_TITLE = "Invoice to Excel"
COLUMNS = [
    "source_file", "supplier_name", "invoice_number", "invoice_date",
    "gstin", "place_of_supply", "currency", "subtotal", "cgst",
    "sgst", "igst", "other_tax", "total_amount", "po_number",
    "extraction_notes"
]

st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="wide")
st.title("🧾 Invoice to Excel")
st.caption("Local-first invoice extraction for Indian small businesses. Review every result before using it.")

with st.sidebar:
    st.header("Privacy & setup")
    st.write("Files are processed by this app in its current Python environment. This MVP does not upload documents to an AI API or send them to a third-party service.")
    st.warning("If you run this on a hosted server, uploaded files are processed on that server. For sensitive invoices, run it locally on your own computer.")
    st.markdown("**Supported input**")
    st.write("PDF invoices and common image formats (PNG, JPG, JPEG, TIFF, BMP, WEBP).")
    st.markdown("**Extraction limits**")
    st.write("Text PDFs work best. Scanned PDFs require optional OCR dependencies. Extraction is heuristic and must be checked.")

def clean_spaces(s):
    return re.sub(r"[ \t]+", " ", (s or "")).strip()

def extract_pdf_text(data):
    if PdfReader is None:
        return "", "Install pypdf to read PDFs."
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages).strip()
        if text:
            return text, ""
        if pytesseract is not None and convert_from_bytes is not None:
            try:
                images = convert_from_bytes(data, dpi=220)
                ocr_text = "\n".join(pytesseract.image_to_string(im) for im in images).strip()
                if ocr_text:
                    return ocr_text, "Scanned PDF processed with local OCR."
            except Exception as e:
                return "", f"No selectable PDF text. OCR fallback failed: {e}"
        return "", "No selectable text found. For scanned PDFs, install Tesseract OCR and pdf2image plus Poppler."
    except Exception as e:
        return "", f"Could not read PDF: {e}"

def extract_image_text(data):
    if pytesseract is None:
        return "", "Image OCR needs Tesseract installed plus: pip install pytesseract"
    try:
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)
        return text.strip(), ""
    except Exception as e:
        return "", f"Could not OCR image: {e}"

def first_match(patterns, text, flags=re.IGNORECASE | re.MULTILINE):
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if m:
            return clean_spaces(m.group(1))
    return ""

def parse_amount(raw):
    if not raw:
        return None
    value = raw.strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    try:
        return round(float(value), 2)
    except ValueError:
        return None

def amount_match(patterns, text):
    raw = first_match(patterns, text)
    return parse_amount(raw)

def extract_invoice_fields(text, filename):
    # Conservative heuristic patterns for common Indian invoice layouts.
    invoice_number = first_match([
        r"(?:invoice\s*(?:no\.?|number|#)|tax\s*invoice\s*(?:no\.?|number|#))\s*[:\-]?\s*([A-Z0-9][A-Z0-9/_\-\.]{1,})",
        r"(?:bill\s*(?:no\.?|number|#))\s*[:\-]?\s*([A-Z0-9][A-Z0-9/_\-\.]{1,})",
    ], text)
    invoice_date = first_match([
        r"(?:invoice\s*date|date\s*of\s*invoice|bill\s*date|dated)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:invoice\s*date|date\s*of\s*invoice|bill\s*date|dated)\s*[:\-]?\s*(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
    ], text)
    gstin = first_match([
        r"(?:GSTIN(?:\s*\/\s*UIN)?|GST\s*IN)\s*[:\-]?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])",
        r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b",
    ], text)
    supplier = first_match([
        r"(?:supplier|seller|vendor|sold\s*by|from)\s*(?:name)?\s*[:\-]\s*([^\n]{3,80})",
    ], text)
    if not supplier:
        excluded = re.compile(r"(tax\s*invoice|invoice|bill\s*to|ship\s*to|gstin|gst\s*in|date|original\s*for|duplicate|triplicate|details|description|qty|quantity|rate|amount|subtotal|total|page\s+\d+)", re.I)
        for line in text.splitlines()[:12]:
            candidate = clean_spaces(line)
            if 3 <= len(candidate) <= 70 and not excluded.search(candidate) and not re.fullmatch(r"[\W\d_]+", candidate):
                supplier = candidate
                break
    po_number = first_match([
        r"(?:purchase\s*order|PO)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9/_\-]{2,})"
    ], text)
    place = first_match([
        r"(?:place\s*of\s*supply|state\s*of\s*supply)\s*[:\-]?\s*([^\n]{2,60})"
    ], text)
    subtotal = amount_match([
        r"(?:taxable\s*value|sub\s*total|subtotal|total\s*before\s*tax)\s*[:₹\- ]*\s*₹?\s*([0-9,]+(?:\.\d{1,2})?)"
    ], text)
    cgst = amount_match([r"\bCGST\b(?:\s+\d+(?:\.\d+)?\s*%)?[^\d₹\n]{0,10}\s*₹?\s*([0-9,]+(?:\.\d{1,2})?)"], text)
    sgst = amount_match([r"\bSGST\b(?:\s+\d+(?:\.\d+)?\s*%)?[^\d₹\n]{0,10}\s*₹?\s*([0-9,]+(?:\.\d{1,2})?)"], text)
    igst = amount_match([r"\bIGST\b(?:\s+\d+(?:\.\d+)?\s*%)?[^\d₹\n]{0,10}\s*₹?\s*([0-9,]+(?:\.\d{1,2})?)"], text)
    total = amount_match([
        r"(?:grand\s*total|invoice\s*total|total\s*amount|net\s*payable|amount\s*payable|total)\s*[:₹\- ]*\s*₹?\s*([0-9,]+(?:\.\d{1,2})?)"
    ], text)
    notes = []
    if not text.strip():
        notes.append("No text extracted; check OCR setup or PDF is image-only.")
    if not invoice_number:
        notes.append("Invoice number not detected.")
    if not invoice_date:
        notes.append("Invoice date not detected.")
    if total is None:
        notes.append("Total amount not detected.")
    if not supplier:
        notes.append("Supplier name not confidently detected; review manually.")
    return {
        "source_file": filename,
        "supplier_name": supplier,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "gstin": gstin,
        "place_of_supply": place,
        "currency": "INR",
        "subtotal": subtotal,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "other_tax": None,
        "total_amount": total,
        "po_number": po_number,
        "extraction_notes": " ".join(notes),
    }

def process_file(uploaded):
    data = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix.lower()
    if suffix == ".pdf":
        text, note = extract_pdf_text(data)
    else:
        text, note = extract_image_text(data)
    result = extract_invoice_fields(text, uploaded.name)
    if note:
        result["extraction_notes"] = (result["extraction_notes"] + " " + note).strip()
    return result, text

st.subheader("1. Upload invoices")
uploads = st.file_uploader(
    "Select one or more invoice PDFs or images",
    type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"],
    accept_multiple_files=True,
    help="Files are processed in this app session. Avoid using confidential documents on a server you do not control."
)

if "invoice_df" not in st.session_state:
    st.session_state.invoice_df = None
if "raw_texts" not in st.session_state:
    st.session_state.raw_texts = {}

if uploads:
    if st.button("Extract invoice fields", type="primary"):
        rows = []
        raw_texts = {}
        progress = st.progress(0)
        status = st.empty()
        for idx, uploaded in enumerate(uploads):
            status.write(f"Processing {uploaded.name} ({idx + 1}/{len(uploads)})…")
            row, raw_text = process_file(uploaded)
            rows.append(row)
            raw_texts[uploaded.name] = raw_text
            progress.progress((idx + 1) / len(uploads))
        st.session_state.invoice_df = pd.DataFrame(rows, columns=COLUMNS)
        st.session_state.raw_texts = raw_texts
        status.success(f"Processed {len(rows)} file(s). Review and correct the extracted values below.")
        progress.empty()

if st.session_state.invoice_df is not None:
    st.subheader("2. Review and correct")
    st.info("Extraction is heuristic, not accounting advice. Verify all values against the source invoice before relying on the spreadsheet.")
    edited = st.data_editor(
        st.session_state.invoice_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="invoice_editor",
        column_config={
            "subtotal": st.column_config.NumberColumn("Subtotal", format="₹%.2f"),
            "cgst": st.column_config.NumberColumn("CGST", format="₹%.2f"),
            "sgst": st.column_config.NumberColumn("SGST", format="₹%.2f"),
            "igst": st.column_config.NumberColumn("IGST", format="₹%.2f"),
            "other_tax": st.column_config.NumberColumn("Other tax", format="₹%.2f"),
            "total_amount": st.column_config.NumberColumn("Total amount", format="₹%.2f"),
            "extraction_notes": st.column_config.TextColumn("Extraction notes", width="large"),
        }
    )
    st.session_state.invoice_df = edited
    c1, c2, c3 = st.columns(3)
    c1.metric("Invoices", len(edited))
    c2.metric("Totals detected", int(edited["total_amount"].notna().sum()))
    c3.metric("Needs review", int(edited["extraction_notes"].fillna("").str.len().gt(0).sum()))

    def make_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Invoices")
            ws = writer.sheets["Invoices"]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for column_cells in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in column_cells), default=10)
                ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 48)
        return output.getvalue()

    excel_bytes = make_excel(edited)
    st.download_button(
        "Download reviewed Excel file",
        data=excel_bytes,
        file_name=f"invoice_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    csv_bytes = edited.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download CSV backup", data=csv_bytes, file_name="invoice_extract.csv", mime="text/csv")

    with st.expander("Inspect extracted text (troubleshooting)"):
        selected = st.selectbox("Choose a processed file", list(st.session_state.raw_texts.keys()))
        st.text_area("Extracted text", st.session_state.raw_texts.get(selected, ""), height=240)

st.divider()
st.caption("MVP limitations: text-based PDFs and clear images work best. OCR requires local Tesseract; scanned PDFs additionally require pdf2image and Poppler. Fields vary across invoice layouts, so always review extracted data.")
