# exporter.py — CSV export logic for single and multi-contract views

import pandas as pd
import io
from src.risk_flagger import flag_risks, get_risk_summary, RED, YELLOW

DISPLAY_COLUMNS = [
    "filename",
    "pricing_structure",
    "payment_terms_days",
    "auto_renewal",
    "renewal_notice_days",
    "sla_uptime_percent",
    "penalty_per_breach",
    "termination_clause",
    "contract_end_date",
    "governing_law",
    "overall_risk",
    "red_flags",
    "yellow_flags",
    "flag_details",
]


def record_to_export_row(record: dict) -> dict:
    """
    Convert a normalized record into a flat export row,
    including risk summary columns.
    """
    flags = flag_risks(record)
    summary = get_risk_summary(flags)

    flag_details = " | ".join([
        f"{f['level']} {f['field']}: {f['message']}" for f in flags
    ])

    row = {col: record.get(col) for col in DISPLAY_COLUMNS if col in record}
    row["overall_risk"] = summary["overall"]
    row["red_flags"] = summary["red_count"]
    row["yellow_flags"] = summary["yellow_count"]
    row["flag_details"] = flag_details if flag_details else "None"

    return row


def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Convert a list of contract records into a display DataFrame."""
    rows = [record_to_export_row(r) for r in records]
    df = pd.DataFrame(rows, columns=DISPLAY_COLUMNS)
    return df


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to CSV bytes for Streamlit download."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def single_record_to_csv_bytes(record: dict) -> bytes:
    """Convenience: single record → CSV bytes."""
    df = records_to_dataframe([record])
    return dataframe_to_csv_bytes(df)
