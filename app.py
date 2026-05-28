# app.py — Vendor Contract Intelligence Tool

import streamlit as st
from src.pdf_parser import get_chunks_for_llm
from src.extractor import extract_from_all_chunks, normalize_contract_record

st.set_page_config(
    page_title="Vendor Contract Intelligence",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Vendor Contract Intelligence Tool")
st.caption("Upload a vendor PDF contract → extract structured terms → flag risks")

uploaded_file = st.file_uploader("Upload a vendor contract PDF", type=["pdf"])

if uploaded_file:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 📑 Parsing")
        with st.spinner("Extracting sections from PDF..."):
            chunks = get_chunks_for_llm(uploaded_file)
        st.success(f"✅ {len(chunks)} section(s) found")

        with st.expander("View raw sections"):
            for chunk in chunks:
                st.markdown(f"**`{chunk['section']}`**")
                st.code(chunk["text"][:400] + ("..." if len(chunk["text"]) > 400 else ""))

    with col2:
        st.markdown("### 🤖 Extracting with Claude")
        with st.spinner("Sending to Claude... (this may take 15–30s)"):
            extracted = extract_from_all_chunks(chunks)
            record = normalize_contract_record(extracted, uploaded_file.name)

        st.success("✅ Extraction complete")
        st.json(record)

else:
    st.info("👆 Upload a PDF to get started.")
