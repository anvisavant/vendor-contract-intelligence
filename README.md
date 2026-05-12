# Vendor Contract Intelligence Tool

A Streamlit app that extracts structured data from vendor PDF contracts using Claude (Anthropic), flags risk terms, and outputs a normalized comparison table.

## Features
- PDF parsing with pdfplumber (multi-page, up to 50 pages)
- LLM extraction via Claude with structured JSON output
- Automatic risk flagging (renewal windows, SLA thresholds, expiry dates)
- CSV export and multi-contract comparison

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY
streamlit run app.py
```

## Project Structure
```
vendor-contract-intelligence/
├── app.py                  # Streamlit main app
├── contracts/              # Drop test PDFs here
├── src/
│   ├── pdf_parser.py       # PDF text extraction + section chunking
│   ├── extractor.py        # LangChain + Claude extraction engine
│   ├── risk_flagger.py     # Risk scoring logic
│   └── exporter.py         # CSV download logic
├── .env                    # API keys (gitignored)
└── requirements.txt
```
