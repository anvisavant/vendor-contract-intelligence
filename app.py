# app.py — Vendor Contract Intelligence Tool

import streamlit as st
from src.pdf_parser import get_chunks_for_llm

st.set_page_config(
    page_title="Vendor Contract Intelligence",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Vendor Contract Intelligence Tool")
st.caption("Upload a vendor PDF contract → extract structured terms → flag risks")

uploaded_file = st.file_uploader("Upload a vendor contract PDF", type=["pdf"])

if uploaded_file:
    with st.spinner("Parsing PDF..."):
        chunks = get_chunks_for_llm(uploaded_file)

    st.success(f"✅ Extracted **{len(chunks)} section(s)** from the contract.")

    with st.expander("🔍 View extracted sections (raw)"):
        for chunk in chunks:
            st.markdown(f"**`{chunk['section']}`**")
            st.code(chunk["text"][:500] + ("..." if len(chunk["text"]) > 500 else ""))
            st.divider()
else:
    st.info("👆 Upload a PDF to get started.")
