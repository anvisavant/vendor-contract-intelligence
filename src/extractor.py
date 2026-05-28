# extractor.py — LangChain + Claude extraction engine

import json
import re
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

# The 9 fields we extract from every contract section
EXTRACTION_FIELDS = [
    "pricing_structure",
    "payment_terms_days",
    "auto_renewal",
    "renewal_notice_days",
    "sla_uptime_percent",
    "penalty_per_breach",
    "termination_clause",
    "contract_end_date",
    "governing_law",
]

EXTRACTION_PROMPT_TEMPLATE = """<instructions>
You are a contract analysis expert. Extract the following fields from the vendor contract section below.
Return a JSON object ONLY — no explanation, no markdown, no code fences.
If a field is not found or not mentioned, return null for that field.

Fields to extract:
- pricing_structure: string describing how pricing works (e.g. "monthly flat fee", "per-seat SaaS", "time & materials")
- payment_terms_days: integer — number of days to pay after invoice (e.g. 30, 45, 60)
- auto_renewal: boolean — true if contract auto-renews, false if it does not, null if not mentioned
- renewal_notice_days: integer — days notice required to cancel before auto-renewal
- sla_uptime_percent: float — guaranteed uptime percentage (e.g. 99.9)
- penalty_per_breach: string — penalty amount or formula per SLA breach (e.g. "$500 per incident", "5% of monthly fee")
- termination_clause: string — brief description of termination rights (e.g. "30 days written notice, either party")
- contract_end_date: string — contract end or expiry date in ISO format YYYY-MM-DD if found, else the raw text
- governing_law: string — governing jurisdiction (e.g. "State of Delaware", "England and Wales")
</instructions>

<document>
{chunk}
</document>"""


def extract_fields_from_chunk(section_name: str, chunk_text: str) -> dict:
    """
    Send one contract chunk to Claude and return extracted fields as a dict.
    Returns a dict with all 9 fields (null for any not found).
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(chunk=chunk_text)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_response = message.content[0].text.strip()
    parsed = _parse_json_response(raw_response)
    parsed["_section"] = section_name
    return parsed


def _parse_json_response(raw: str) -> dict:
    """
    Safely parse Claude's JSON response.
    Strips markdown fences if present, falls back to empty nulls on failure.
    """
    # Strip ```json ... ``` fences if Claude added them despite instructions
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
        # Ensure all expected fields are present
        for field in EXTRACTION_FIELDS:
            if field not in data:
                data[field] = None
        return data
    except json.JSONDecodeError:
        # Graceful fallback — return nulls for all fields
        return {field: None for field in EXTRACTION_FIELDS}


def extract_from_all_chunks(chunks: list[dict]) -> dict:
    """
    Run extraction over all chunks and merge results into one flat record.
    Later chunks overwrite earlier ones only if the field was null before.
    Returns a single merged dict representing the full contract.
    """
    merged = {field: None for field in EXTRACTION_FIELDS}
    section_results = []

    for chunk in chunks:
        result = extract_fields_from_chunk(chunk["section"], chunk["text"])
        section_results.append(result)

        for field in EXTRACTION_FIELDS:
            val = result.get(field)
            # Only overwrite if we have a new non-null value
            if val is not None and merged[field] is None:
                merged[field] = val

    merged["_raw_section_results"] = section_results
    return merged


def normalize_contract_record(extracted: dict, filename: str) -> dict:
    """
    Clean and normalize the merged extraction result into a display-ready record.
    Coerces types and adds the source filename.
    """
    record = {"filename": filename}

    for field in EXTRACTION_FIELDS:
        val = extracted.get(field)

        # Type coercions
        if field == "payment_terms_days" and val is not None:
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = None

        if field == "renewal_notice_days" and val is not None:
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = None

        if field == "sla_uptime_percent" and val is not None:
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = None

        if field == "auto_renewal" and val is not None:
            if isinstance(val, str):
                val = val.lower() in ("true", "yes", "1")

        record[field] = val

    return record
