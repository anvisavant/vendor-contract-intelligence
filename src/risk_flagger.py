# risk_flagger.py — Risk scoring logic for extracted contract fields

from datetime import datetime, date
from typing import Optional

# Risk levels
RED = "🔴"
YELLOW = "🟡"
GREEN = "🟢"

def flag_risks(record: dict) -> list[dict]:
    """
    Run all risk checks against a normalized contract record.
    Returns a list of flag dicts: { field, level, message, value }
    """
    flags = []

    flags += _check_renewal_notice(record)
    flags += _check_auto_renewal_no_notice(record)
    flags += _check_sla_uptime(record)
    flags += _check_penalty_clause(record)
    flags += _check_contract_expiry(record)
    flags += _check_payment_terms(record)

    return flags


def _check_renewal_notice(record: dict) -> list[dict]:
    """🔴 Short renewal window — notice period under 30 days."""
    days = record.get("renewal_notice_days")
    if days is None:
        return []
    if days < 30:
        return [{
            "field": "renewal_notice_days",
            "level": RED,
            "message": f"Short renewal notice window: only {days} days to cancel before auto-renewal.",
            "value": days,
            "recommendation": "Negotiate to at least 30–60 days notice period."
        }]
    return []


def _check_auto_renewal_no_notice(record: dict) -> list[dict]:
    """🔴 Auto-renews but no notice period defined — silent lock-in risk."""
    auto = record.get("auto_renewal")
    notice = record.get("renewal_notice_days")
    if auto is True and notice is None:
        return [{
            "field": "auto_renewal",
            "level": RED,
            "message": "Contract auto-renews with no defined notice period — silent lock-in risk.",
            "value": "auto_renewal=True, renewal_notice_days=null",
            "recommendation": "Require explicit cancellation notice window before signing."
        }]
    return []


def _check_sla_uptime(record: dict) -> list[dict]:
    """🟡 Below-standard SLA — uptime under 99.5%."""
    uptime = record.get("sla_uptime_percent")
    if uptime is None:
        return [{
            "field": "sla_uptime_percent",
            "level": YELLOW,
            "message": "No SLA uptime guarantee found in contract.",
            "value": None,
            "recommendation": "Request a minimum 99.5% uptime SLA with defined measurement window."
        }]
    if uptime < 99.5:
        return [{
            "field": "sla_uptime_percent",
            "level": YELLOW,
            "message": f"SLA uptime of {uptime}% is below the 99.5% industry standard.",
            "value": uptime,
            "recommendation": "Negotiate uptime to 99.5% or above. At 99.0%, that's ~87 hours downtime/year."
        }]
    return []


def _check_penalty_clause(record: dict) -> list[dict]:
    """🟡 No penalty clause — vendor has no financial consequence for SLA breach."""
    penalty = record.get("penalty_per_breach")
    if penalty is None:
        return [{
            "field": "penalty_per_breach",
            "level": YELLOW,
            "message": "No penalty or remedy clause found for SLA breaches.",
            "value": None,
            "recommendation": "Add service credits (e.g. 5–10% of monthly fee per breach incident)."
        }]
    return []


def _check_contract_expiry(record: dict) -> list[dict]:
    """🔴 Contract expiring within 90 days."""
    end_date_raw = record.get("contract_end_date")
    if end_date_raw is None:
        return []

    parsed = _parse_date(end_date_raw)
    if parsed is None:
        return []

    today = date.today()
    days_remaining = (parsed - today).days

    if days_remaining < 0:
        return [{
            "field": "contract_end_date",
            "level": RED,
            "message": f"Contract has already expired ({parsed.strftime('%b %d, %Y')}, {abs(days_remaining)} days ago).",
            "value": str(parsed),
            "recommendation": "Confirm whether contract was renewed or is operating without coverage."
        }]
    elif days_remaining <= 90:
        return [{
            "field": "contract_end_date",
            "level": RED,
            "message": f"Contract expires in {days_remaining} days ({parsed.strftime('%b %d, %Y')}) — within 90-day alert window.",
            "value": str(parsed),
            "recommendation": "Initiate renewal or replacement procurement immediately."
        }]
    return []


def _check_payment_terms(record: dict) -> list[dict]:
    """🟡 Unusually short payment terms (under 15 days)."""
    days = record.get("payment_terms_days")
    if days is None:
        return []
    if days < 15:
        return [{
            "field": "payment_terms_days",
            "level": YELLOW,
            "message": f"Payment terms of {days} days are unusually short — cash flow risk.",
            "value": days,
            "recommendation": "Standard is Net-30. Negotiate to at least 30 days."
        }]
    return []


def _parse_date(raw: str) -> Optional[date]:
    """Try multiple date formats to parse a contract end date string."""
    if not isinstance(raw, str):
        return None

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def summarize_risk_level(flags: list[dict]) -> str:
    """Return overall risk level based on highest severity flag."""
    if not flags:
        return GREEN
    levels = [f["level"] for f in flags]
    if RED in levels:
        return RED
    if YELLOW in levels:
        return YELLOW
    return GREEN


def get_risk_summary(flags: list[dict]) -> dict:
    """Return counts and overall level for dashboard display."""
    red_count = sum(1 for f in flags if f["level"] == RED)
    yellow_count = sum(1 for f in flags if f["level"] == YELLOW)
    return {
        "overall": summarize_risk_level(flags),
        "red_count": red_count,
        "yellow_count": yellow_count,
        "total_flags": len(flags),
        "flags": flags
    }
