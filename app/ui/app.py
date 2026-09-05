from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("Multimodal AI Workbench")
st.caption("Deterministic workflow routing, evidence-first analysis, and traceable delivery.")

user_query = st.text_area("User query", value="Analyze this maintenance report and sensor dataset. Tell me if there is evidence of equipment failure and generate a report.")
requested_deliverable = st.selectbox("Requested output", ["report", "docx", "xlsx", "pptx"])
files = st.file_uploader("Upload files", accept_multiple_files=True)

if st.button("Run analysis"):
    payload = {"user_query": user_query, "requested_deliverable": requested_deliverable}
    uploaded_files = []
    for uploaded_file in files or []:
        uploaded_files.append((uploaded_file.name, uploaded_file.read(), uploaded_file.type))
    response = requests.post(
        f"{BACKEND_URL}/analyze",
        data=payload,
        files=[("files", (name, content, mime)) for name, content, mime in uploaded_files],
        timeout=300,
    )
    if response.ok:
        data = response.json()
        st.success("Analysis complete")
        st.subheader("Final answer")
        st.write(data.get("final_answer"))
        st.subheader("Evidence")
        st.write(data.get("evidence"))
        st.subheader("Verification status")
        st.write(data.get("verification_status"))
        st.subheader("Traceability")
        st.write(data.get("traceability"))
        if data.get("generated_deliverables"):
            st.subheader("Download")
            for file_name in data["generated_deliverables"]:
                st.markdown(f"[Download {file_name}]({BACKEND_URL}/download/{data['request_id']}/{Path(file_name).name})")
    else:
        st.error(f"Request failed: {response.text}")
