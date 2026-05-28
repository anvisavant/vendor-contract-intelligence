# app.py — Vendor Contract Intelligence Tool
# Full production version with single-contract analysis + multi-contract comparison

import streamlit as st
import pandas as pd
from src.pdf_parser import get_chunks_for_llm
from src.extractor import extract_from_all_chunks, normalize_contract_record
from src.risk_flagger import flag_risks, get_risk_summary, RED, YELLOW, GREEN
from src.exporter import records_to_dataframe, dataframe_to_csv_bytes

st.set_page_config(
    page_title="Vendor Contract Intelligence",
    page_icon="📄",
    layout="wide"
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .risk-red    { background:#fee2e2; border-left:4px solid #ef4444; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
    .risk-yellow { background:#fef9c3; border-left:4px solid #eab308; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
    .risk-green  { background:#dcfce7; border-left:4px solid #22c55e; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
    .field-row   { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f0f0f0; }
    .field-label { color:#6b7280; font-size:0.85rem; }
    .field-value { font-weight:500; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Vendor Contract Intelligence")
st.caption("Upload vendor PDF contracts → Claude extracts key terms → automatic risk flagging")
st.divider()

# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio("Mode", ["Single Contract Analysis", "Multi-Contract Comparison"], horizontal=True)
st.divider()


def process_contract(uploaded_file):
    """Full pipeline: PDF → chunks → Claude extraction → normalized record."""
    with st.spinner(f"Parsing {uploaded_file.name}..."):
        chunks = get_chunks_for_llm(uploaded_file)
    with st.spinner(f"Extracting fields via Claude ({len(chunks)} sections)..."):
        extracted = extract_from_all_chunks(chunks)
        record = normalize_contract_record(extracted, uploaded_file.name)
    return record, chunks


def render_risk_flags(flags):
    if not flags:
        st.markdown('<div class="risk-green">✅ <strong>No risk flags detected.</strong> Contract terms appear standard.</div>', unsafe_allow_html=True)
        return
    for flag in flags:
        css_class = "risk-red" if flag["level"] == RED else "risk-yellow"
        st.markdown(f"""
        <div class="{css_class}">
            <strong>{flag['level']} {flag['field'].replace('_',' ').title()}</strong><br>
            {flag['message']}<br>
            <span style="color:#6b7280;font-size:0.85rem;">💡 {flag['recommendation']}</span>
        </div>
        """, unsafe_allow_html=True)


def render_extracted_fields(record):
    field_labels = {
        "pricing_structure":    "Pricing Structure",
        "payment_terms_days":   "Payment Terms (days)",
        "auto_renewal":         "Auto-Renewal",
        "renewal_notice_days":  "Renewal Notice (days)",
        "sla_uptime_percent":   "SLA Uptime (%)",
        "penalty_per_breach":   "Penalty per Breach",
        "termination_clause":   "Termination Clause",
        "contract_end_date":    "Contract End Date",
        "governing_law":        "Governing Law",
    }
    for field, label in field_labels.items():
        val = record.get(field)
        display = str(val) if val is not None else "—"
        if field == "auto_renewal" and val is not None:
            display = "✅ Yes" if val else "❌ No"
        st.markdown(
            f'<div class="field-row"><span class="field-label">{label}</span>'
            f'<span class="field-value">{display}</span></div>',
            unsafe_allow_html=True
        )


# ── SINGLE CONTRACT MODE ──────────────────────────────────────────────────────
if mode == "Single Contract Analysis":
    uploaded_file = st.file_uploader("Upload a vendor contract PDF", type=["pdf"])

    if uploaded_file:
        record, chunks = process_contract(uploaded_file)
        flags = flag_risks(record)
        summary = get_risk_summary(flags)

        # Metric bar
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Risk", summary["overall"])
        c2.metric("🔴 Critical", summary["red_count"])
        c3.metric("🟡 Warnings", summary["yellow_count"])
        c4.metric("Sections Parsed", len(chunks))
        st.divider()

        left, right = st.columns([1, 1], gap="large")
        with left:
            st.markdown("### 📋 Extracted Terms")
            render_extracted_fields(record)

            st.markdown("<br>", unsafe_allow_html=True)
            csv_bytes = dataframe_to_csv_bytes(records_to_dataframe([record]))
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv_bytes,
                file_name=f"{uploaded_file.name.replace('.pdf','')}_extracted.csv",
                mime="text/csv"
            )

        with right:
            st.markdown("### 🚨 Risk Flags")
            render_risk_flags(flags)

        with st.expander("🔍 View raw extracted sections"):
            for chunk in chunks:
                st.markdown(f"**`{chunk['section']}`**")
                st.code(chunk["text"][:500] + ("..." if len(chunk["text"]) > 500 else ""), language=None)

    else:
        st.info("👆 Upload a vendor contract PDF to begin analysis.")


# ── MULTI-CONTRACT COMPARISON MODE ───────────────────────────────────────────
else:
    uploaded_files = st.file_uploader(
        "Upload 2–3 vendor contract PDFs for comparison",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files and len(uploaded_files) >= 2:
        records = []
        for f in uploaded_files[:3]:
            st.markdown(f"**Processing:** `{f.name}`")
            record, _ = process_contract(f)
            records.append(record)

        st.success(f"✅ Processed {len(records)} contracts")
        st.divider()

        # Build comparison dataframe
        df = records_to_dataframe(records)

        st.markdown("### 📊 Side-by-Side Comparison")

        # Highlight best/worst per numeric column
        numeric_cols = ["payment_terms_days", "renewal_notice_days", "sla_uptime_percent"]

        def highlight_comparison(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            for col in numeric_cols:
                if col not in df.columns:
                    continue
                vals = pd.to_numeric(df[col], errors="coerce")
                if vals.isna().all():
                    continue
                if col == "sla_uptime_percent":
                    best_idx = vals.idxmax()
                    worst_idx = vals.idxmin()
                else:
                    best_idx = vals.idxmax()
                    worst_idx = vals.idxmin()
                styles.loc[best_idx, col] = "background-color: #dcfce7"
                styles.loc[worst_idx, col] = "background-color: #fee2e2"
            return styles

        display_df = df[["filename", "pricing_structure", "payment_terms_days",
                          "auto_renewal", "renewal_notice_days", "sla_uptime_percent",
                          "penalty_per_breach", "contract_end_date", "governing_law",
                          "overall_risk", "red_flags", "yellow_flags"]].copy()

        st.dataframe(
            display_df.style.apply(highlight_comparison, axis=None),
            use_container_width=True,
            height=200
        )

        st.markdown("### 🚨 Risk Flags by Contract")
        for record in records:
            flags = flag_risks(record)
            summary = get_risk_summary(flags)
            with st.expander(f"{summary['overall']} {record['filename']} — {summary['total_flags']} flag(s)"):
                render_risk_flags(flags)

        csv_bytes = dataframe_to_csv_bytes(df)
        st.download_button(
            label="⬇️ Download Full Comparison CSV",
            data=csv_bytes,
            file_name="contract_comparison.csv",
            mime="text/csv"
        )

    elif uploaded_files and len(uploaded_files) == 1:
        st.warning("Upload at least 2 contracts to compare.")
    else:
        st.info("👆 Upload 2–3 vendor contract PDFs to compare them side by side.")
