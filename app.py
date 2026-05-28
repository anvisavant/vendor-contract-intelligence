# app.py — Vendor Contract Intelligence Tool

import streamlit as st
from src.pdf_parser import get_chunks_for_llm
from src.extractor import extract_from_all_chunks, normalize_contract_record
from src.risk_flagger import flag_risks, get_risk_summary, RED, YELLOW, GREEN

st.set_page_config(
    page_title="Vendor Contract Intelligence",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Vendor Contract Intelligence Tool")
st.caption("Upload a vendor PDF contract → extract structured terms → flag risks")

uploaded_file = st.file_uploader("Upload a vendor contract PDF", type=["pdf"])

if uploaded_file:

    # ── Step 1: Parse ──────────────────────────────────────────────
    with st.spinner("Parsing PDF sections..."):
        chunks = get_chunks_for_llm(uploaded_file)

    # ── Step 2: Extract ────────────────────────────────────────────
    with st.spinner(f"Extracting fields from {len(chunks)} section(s) via Claude..."):
        extracted = extract_from_all_chunks(chunks)
        record = normalize_contract_record(extracted, uploaded_file.name)

    # ── Step 3: Flag risks ────────────────────────────────────────
    flags = flag_risks(record)
    summary = get_risk_summary(flags)

    # ── Layout ────────────────────────────────────────────────────
    st.markdown("---")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Overall Risk", summary["overall"])
    metric_col2.metric("🔴 Critical Flags", summary["red_count"])
    metric_col3.metric("🟡 Warning Flags", summary["yellow_count"])
    metric_col4.metric("Sections Parsed", len(chunks))

    st.markdown("---")
    left, right = st.columns([1, 1])

    with left:
        st.markdown("### 📋 Extracted Terms")
        display_fields = {
            "Pricing Structure": record.get("pricing_structure"),
            "Payment Terms (days)": record.get("payment_terms_days"),
            "Auto-Renewal": record.get("auto_renewal"),
            "Renewal Notice (days)": record.get("renewal_notice_days"),
            "SLA Uptime (%)": record.get("sla_uptime_percent"),
            "Penalty per Breach": record.get("penalty_per_breach"),
            "Termination Clause": record.get("termination_clause"),
            "Contract End Date": record.get("contract_end_date"),
            "Governing Law": record.get("governing_law"),
        }
        for label, val in display_fields.items():
            display_val = str(val) if val is not None else "—"
            st.markdown(f"**{label}:** {display_val}")

    with right:
        st.markdown("### 🚨 Risk Flags")
        if not flags:
            st.success("✅ No risk flags detected.")
        else:
            for flag in flags:
                color = "red" if flag["level"] == RED else "orange"
                with st.container():
                    st.markdown(
                        f"{flag['level']} **{flag['field']}** — {flag['message']}"
                    )
                    st.caption(f"💡 {flag['recommendation']}")
                    st.divider()

    with st.expander("🔍 Raw extracted sections"):
        for chunk in chunks:
            st.markdown(f"**`{chunk['section']}`**")
            st.code(chunk["text"][:400] + ("..." if len(chunk["text"]) > 400 else ""))

else:
    st.info("👆 Upload a PDF to get started.")
