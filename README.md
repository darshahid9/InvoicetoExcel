# Invoice to Excel — Local-First MVP

A browser-based Streamlit app that extracts common invoice fields from PDF files and invoice images, lets the user review/correct the results, and exports Excel or CSV.

## Features

- Batch upload of PDFs and common image formats.
- Text extraction from text-based PDFs using `pypdf`.
- OCR for invoice images using local Tesseract.
- Optional OCR fallback for scanned PDFs using `pdf2image` + Poppler + Tesseract.
- Heuristic extraction of supplier, invoice number/date, GSTIN, place of supply, subtotal, tax fields, total, and PO number.
- Editable review table before export.
- Excel export with frozen header, filters, and reasonable column widths.
- CSV backup export.
- No AI API key or cloud AI service required.

## Privacy

This app does not intentionally send documents to an external service. Uploaded files are processed by the Python process running Streamlit. Run it on your own computer for sensitive invoices. If deployed to a hosted server later, documents would be processed on that server and the privacy statement must be updated accordingly.

## Requirements

- Python 3.10–3.12 recommended.
- For image OCR: Tesseract OCR installed on your computer.
- For scanned PDF OCR: Tesseract plus Poppler, and the Python package `pdf2image`.

### macOS setup

If Homebrew is installed:

```bash
brew install tesseract poppler
```

### Ubuntu/Debian setup

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

### Windows setup

Install Tesseract OCR and Poppler separately, and ensure their executable folders are on PATH. The app still supports text-based PDFs even if OCR is not installed.

## Install and run

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

## Workflow

1. Upload one or more invoice PDFs or images.
2. Click **Extract invoice fields**.
3. Review and edit every field, especially amounts, dates, and GSTIN.
4. Download the reviewed Excel file or CSV backup.

## Extraction caveats

- Invoice layouts differ widely. Extraction uses conservative regular expressions and is not guaranteed to detect every field.
- OCR accuracy depends on image quality, language, rotation, and scan quality.
- Tax amounts can appear in tables in many formats; check them against the invoice.
- `total_amount` is the first matching total-like label, not a verified accounting calculation.
- `supplier_name` detection is intentionally conservative.
- This tool is not accounting, GST filing, or tax advice software.

## Test

Run:

```bash
python -m unittest test_app.py
```

Tests cover representative field extraction patterns and amount parsing. They do not replace manual validation against real invoice formats.
