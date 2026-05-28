# pdf_parser.py — PDF text extraction + section chunking

import pdfplumber
import re
from typing import Optional

# Section headers commonly found in vendor contracts
SECTION_HEADERS = [
    "payment terms", "payment schedule", "pricing", "fees", "compensation",
    "termination", "cancellation", "expiration",
    "service level", "sla", "uptime", "availability",
    "auto-renewal", "renewal", "term",
    "governing law", "jurisdiction", "dispute resolution",
    "liability", "indemnification", "warranty",
    "confidentiality", "non-disclosure",
    "intellectual property", "ownership",
    "scope of services", "deliverables",
    "penalties", "liquidated damages",
]

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract raw text from an uploaded PDF file object (Streamlit UploadedFile or file path).
    Handles multi-page documents up to 50 pages.
    Returns concatenated text with page separators.
    """
    full_text = []

    with pdfplumber.open(pdf_file) as pdf:
        pages_to_read = min(len(pdf.pages), 50)
        for i, page in enumerate(pdf.pages[:pages_to_read]):
            text = page.extract_text()
            if text:
                full_text.append(f"\n--- PAGE {i + 1} ---\n{text}")

    return "\n".join(full_text)


def chunk_by_sections(raw_text: str) -> dict[str, str]:
    """
    Split raw contract text into named sections using header detection.
    Returns a dict: { section_name: section_text }
    Falls back to a single "full_document" chunk if no headers are found.
    """
    lines = raw_text.split("\n")
    sections = {}
    current_section = "preamble"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        matched_header = _match_section_header(stripped)

        if matched_header:
            # Save the previous section
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = matched_header
            current_lines = [line]
        else:
            current_lines.append(line)

    # Save the last section
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    # Fallback: no headers detected → treat as one chunk
    if len(sections) <= 1:
        sections = {"full_document": raw_text}

    return sections


def _match_section_header(line: str) -> Optional[str]:
    """
    Check if a line looks like a section header.
    Returns a normalized header name or None.
    """
    # Strip numbering like "3.", "3.1", "III." from the start
    cleaned = re.sub(r"^[\d\.]+\s*|^[IVXLCDM]+\.\s*", "", line, flags=re.IGNORECASE).strip()
    lower = cleaned.lower()

    # Must be reasonably short to be a header (not a paragraph)
    if len(cleaned) > 80:
        return None

    for header in SECTION_HEADERS:
        if header in lower:
            # Normalize to snake_case key
            key = re.sub(r"\s+", "_", cleaned.lower())
            key = re.sub(r"[^a-z0-9_]", "", key)
            return key

    # Also detect ALL-CAPS lines as headers (common in legal docs)
    if cleaned.isupper() and 3 < len(cleaned) < 60:
        key = re.sub(r"\s+", "_", cleaned.lower())
        key = re.sub(r"[^a-z0-9_]", "", key)
        return key

    return None


def get_chunks_for_llm(pdf_file, max_chunk_chars: int = 3000) -> list[dict]:
    """
    Full pipeline: PDF → raw text → sections → LLM-ready chunks.
    Each chunk is a dict: { "section": str, "text": str }
    Long sections are sub-chunked to stay within max_chunk_chars.
    """
    raw_text = extract_text_from_pdf(pdf_file)
    sections = chunk_by_sections(raw_text)

    chunks = []
    for section_name, section_text in sections.items():
        if not section_text.strip():
            continue

        # Sub-chunk if section is too long
        if len(section_text) <= max_chunk_chars:
            chunks.append({"section": section_name, "text": section_text})
        else:
            sub_chunks = _split_long_section(section_text, max_chunk_chars)
            for idx, sub in enumerate(sub_chunks):
                chunks.append({
                    "section": f"{section_name}_part{idx + 1}",
                    "text": sub
                })

    return chunks


def _split_long_section(text: str, max_chars: int) -> list[str]:
    """Split a long section into overlapping chunks by paragraph."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            # Overlap: keep last paragraph for context
            current = [current[-1], para]
            current_len = len(current[-2]) + len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text[:max_chars]]
