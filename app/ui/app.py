import requests
import streamlit as st
from pathlib import Path


BACKEND_URL = "http://localhost:8000/analyze"


st.set_page_config(
    page_title="SOVARA",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -----------------------------
# Header
# -----------------------------

st.title("🧠 SOVARA")
st.caption(
    "Sovereign Orchestration for Verified AI Reasoning & Automation"
)

st.divider()


# -----------------------------
# Input Section
# -----------------------------

st.subheader("Analysis Request")

query = st.text_area(
    "What would you like SOVARA to analyze?",
    placeholder=(
        "Example: Compare the proposed solution in the document "
        "with the visual architecture and identify the key insights."
    ),
    height=110,
)

uploaded_files = st.file_uploader(
    "Upload your evidence",
    type=["pdf", "png", "jpg", "jpeg", "xlsx", "csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.caption(
        f"📎 {len(uploaded_files)} file(s) ready for analysis"
    )

    cols = st.columns(min(len(uploaded_files), 4))

    for index, file in enumerate(uploaded_files):
        with cols[index % len(cols)]:
            st.write(f"**{file.name}**")


st.divider()


# -----------------------------
# Analyze
# -----------------------------

analyze = st.button(
    "🚀 Analyze with SOVARA",
    type="primary",
    use_container_width=True,
)


if analyze:

    if not query.strip():
        st.warning("Please enter an analysis request.")
        st.stop()

    if not uploaded_files:
        st.warning("Please upload at least one file.")
        st.stop()

    files = [
        (
            "files",
            (
                file.name,
                file.getvalue(),
                file.type or "application/octet-stream",
            ),
        )
        for file in uploaded_files
    ]

    payload = {
        "user_query": query,
        "output_format": "docx",
    }

    with st.spinner(
        "SOVARA is analyzing your evidence and verifying the result..."
    ):
        try:
            response = requests.post(
                BACKEND_URL,
                data=payload,
                files=files,
                timeout=900,
            )

        except requests.exceptions.Timeout:
            st.error(
                "The analysis is taking longer than expected. "
                "Please check the backend terminal."
            )
            st.stop()

        except requests.exceptions.ConnectionError:
            st.error(
                "Could not connect to the SOVARA backend. "
                "Make sure FastAPI is running on port 8000."
            )
            st.stop()

        except Exception as exc:
            st.error(f"Backend connection failed: {exc}")
            st.stop()

    if response.status_code != 200:
        st.error(
            f"SOVARA returned an error "
            f"(HTTP {response.status_code})."
        )

        try:
            st.json(response.json())
        except Exception:
            st.code(response.text)

        st.stop()

    try:
        result = response.json()
    except Exception:
        st.error("Backend returned an invalid JSON response.")
        st.code(response.text)
        st.stop()


    # -----------------------------
    # Extract response
    # -----------------------------

    final_answer = result.get(
        "final_answer",
        result.get("answer", ""),
    )

    verification_results = result.get(
        "verification_results",
        {},
    )

    if isinstance(verification_results, list):
        verification = (
            verification_results[0]
            if verification_results
            else {}
        )
    else:
        verification = verification_results or {}

    evidence = result.get(
        "evidence",
        [],
    )

    vision_results = result.get(
    "vision_results",
    [],
    )

    trace = result.get(
        "traceability",
        [],
    )

    deliverables = result.get(
        "generated_deliverables",
        [],
    )

    telemetry = result.get(
        "execution_telemetry",
        {},
    )


    # -----------------------------
    # Analysis Overview
    # -----------------------------

    st.subheader("Analysis Overview")

    verification_status = (
        verification.get("verification_status")
        if isinstance(verification, dict)
        else None
    )

    if verification_status == "passed":
        status_label = "✅ VERIFIED"
    elif verification_status:
        status_label = "⚠️ REVIEW"
    else:
        status_label = "—"

    file_types = []

    for file in uploaded_files:
        extension = file.name.lower().split(".")[-1]

        if extension == "pdf":
            file_types.append("PDF")
        elif extension in {"png", "jpg", "jpeg"}:
            file_types.append("IMAGE")
        elif extension in {"csv", "xlsx"}:
            file_types.append("DATA")

    modality_label = " + ".join(dict.fromkeys(file_types))

    models = telemetry.get("models_used", [])

    if not models:
        models = []

    trace_count = len(trace) if isinstance(trace, list) else 0

    report_available = bool(deliverables)

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric(
            "Verification",
            status_label,
        )

    with metric2:
        st.metric(
            "Input",
            modality_label or "MULTIMODAL",
        )

    with metric3:
        st.metric(
            "Workflow Steps",
            trace_count,
        )

    with metric4:
        st.metric(
            "Report",
            "READY" if report_available else "—",
        )


    # -----------------------------
    # Models
    # -----------------------------

    st.markdown("### Models Used")

    model_cols = st.columns(2)

    reasoning_model = "Qwen3 4B"
    vision_model = "Gemma 3 4B"

    with model_cols[0]:
        st.info(
            f"🧠 **Reasoning**\n\n"
            f"{reasoning_model}"
        )

    with model_cols[1]:
        st.info(
            f"👁️ **Vision**\n\n"
            f"{vision_model}"
        )


    # -----------------------------
    # Final Result
    # -----------------------------

    st.divider()

    st.subheader("SOVARA Result")

    if final_answer:
        st.markdown(final_answer)
    else:
        st.warning(
            "SOVARA completed the workflow but did not return "
            "a final answer."
        )


    # -----------------------------
    # Evidence
    # -----------------------------

    st.divider()

    st.subheader("Evidence")

    document_evidence = []
    vision_evidence = []

    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue

            evidence_type = item.get(
                "evidence_type",
                "",
            ).lower()

            if evidence_type == "vision":
                vision_evidence.append(item)
            else:
                document_evidence.append(item)

    tabs = st.tabs(
        [
            "📄 Document Evidence",
            "👁️ Vision Evidence",
        ]
    )


    # -----------------------------
    # Document Evidence
    # -----------------------------

    with tabs[0]:

        if not document_evidence:
            st.caption(
                "No document evidence was returned."
            )

        else:

            for index, item in enumerate(
                document_evidence,
                start=1,
            ):

                source = item.get(
                    "source_filename",
                    "Unknown source",
                )

                page = item.get(
                    "page_number",
                    "—",
                )

                evidence_id = item.get(
                    "evidence_id",
                    "unknown",
                )

                content = (
                    item.get("content")
                    or item.get("text")
                    or ""
                )

                with st.container(border=True):

                    st.markdown(
                        f"**Evidence {index}**  \n"
                        f"📄 `{source}` · Page `{page}`"
                    )

                    if content:
                        st.write(content)

                    st.caption(
                        f"Evidence ID: `{evidence_id}`"
                    )


    # -----------------------------
    # Vision Evidence
    # -----------------------------

    with tabs[1]:

        if vision_evidence:

            for index, item in enumerate(
                vision_evidence,
                start=1,
            ):

                source = item.get(
                    "source_filename",
                    "Unknown image",
                )

                evidence_id = item.get(
                    "evidence_id",
                    "unknown",
                )

                content = (
                    item.get("content")
                    or item.get("description")
                    or ""
                )

                confidence = item.get(
                    "confidence",
                )

                with st.container(border=True):

                    st.markdown(
                        f"**Visual Observation {index}**  \n"
                        f"🖼️ `{source}`"
                    )

                    if content:
                        st.write(content)

                    if confidence is not None:
                        st.caption(
                            f"Confidence: {confidence}"
                        )

                    st.caption(
                        f"Evidence ID: `{evidence_id}`"
                    )

        elif vision_results:

            for index, item in enumerate(
                vision_results,
                start=1,
            ):

                source = item.get(
                    "source_file",
                    "Unknown image",
                )

                result_data = item.get(
                    "result",
                    {},
                )

                observations = (
                    result_data.get(
                        "observations",
                        []
                    )
                    if isinstance(result_data, dict)
                    else []
                )

                with st.container(border=True):

                    st.markdown(
                        f"**Image {index}**  \n"
                        f"🖼️ `{source}`"
                    )

                    for obs_index, observation in enumerate(
                        observations,
                        start=1,
                    ):

                        description = (
                            observation.get(
                                "description",
                                "",
                            )
                            if isinstance(observation, dict)
                            else str(observation)
                        )

                        if description:
                            st.write(
                                f"**Observation {obs_index}:** "
                                f"{description}"
                            )

        else:
            st.caption(
                "No vision evidence was returned."
            )


    # -----------------------------
    # Verification
    # -----------------------------

    st.divider()

    st.subheader("Verification")

    if isinstance(verification, dict):

        verification_status = verification.get(
            "verification_status",
            result.get(
                "verification_status",
                "unknown",
            ),
        )

        if verification_status == "passed":

            st.success(
                "✅ VERIFIED — The generated answer "
                "passed the verification stage."
            )

        elif verification_status in {
            "failed",
            "failed_terminal",
        }:

            st.error(
                "❌ Verification failed."
            )

        else:

            st.warning(
                f"Verification status: "
                f"{verification_status}"
            )

        failures = verification.get(
            "failures",
            [],
        )

        numeric_validation = verification.get(
            "numeric_validation",
            [],
        )

        if failures:

            with st.expander(
                "Verification Issues",
                expanded=False,
            ):

                for failure in failures:
                    st.write(
                        f"• {failure}"
                    )

        if numeric_validation:

            with st.expander(
                "Numeric Validation",
                expanded=False,
            ):

                st.json(
                    numeric_validation
                )

    else:

        status = result.get(
            "verification_status",
            "unknown",
        )

        if status == "passed":

            st.success(
                "✅ VERIFIED — The generated answer "
                "passed the verification stage."
            )

        elif status in {
            "failed",
            "failed_terminal",
        }:

            st.error(
                "❌ Verification failed."
            )

        else:

            st.warning(
                f"Verification status: {status}"
            )


    # -----------------------------
    # Execution Trace
    # -----------------------------

    st.divider()

    st.subheader("Execution Trace")

    if isinstance(trace, list) and trace:

        st.caption(
            f"{len(trace)} workflow stages executed"
        )

        with st.expander(
            "View workflow execution",
            expanded=False,
        ):

            for index, step in enumerate(
                trace,
                start=1,
            ):

                if not isinstance(step, dict):
                    st.write(
                        f"{index}. {step}"
                    )
                    continue

                node_name = step.get(
                    "node_name",
                    step.get(
                        "node",
                        "Unknown node",
                    ),
                )

                model_used = step.get(
                    "model_used",
                    "",
                )

                tools_used = step.get(
                    "tools_used",
                    [],
                )

                label = f"**{index}. {node_name}**"

                if model_used:
                    label += f" · `{model_used}`"

                st.markdown(label)

                if tools_used:
                    st.caption(
                        "Tools: "
                        + ", ".join(
                            str(tool)
                            for tool in tools_used
                        )
                    )

    else:
        st.caption(
            "No execution trace returned."
        )


    # -----------------------------
    # Generated Deliverables
    # -----------------------------

    st.divider()

    st.subheader("Generated Deliverables")

    if deliverables:

        request_id = result.get(
            "request_id",
            "",
        )

        for index, deliverable in enumerate(
            deliverables
        ):

            if isinstance(deliverable, dict):

                filename = (
                    deliverable.get("filename")
                    or deliverable.get("name")
                    or deliverable.get("file_name")
                    or "generated_report.docx"
                )

            else:

                filename = Path(
                    str(deliverable)
                ).name

            download_url = (
                f"http://localhost:8000/download/"
                f"{request_id}/{filename}"
            )

            st.markdown(
                f"📄 **{filename}**"
            )

            st.link_button(
                "⬇️ Download Report",
                download_url,
                use_container_width=False,
            )

    else:

        st.caption(
            "No deliverables were generated."
        )


    # -----------------------------
    # Developer Data
    # -----------------------------

    st.divider()

    with st.expander(
        "Developer / Debug Data",
        expanded=False,
    ):

        st.json(
    {
        "request_id": result.get("request_id"),
        "status": result.get("status"),
        "telemetry": telemetry,
        "verification_status": result.get(
            "verification_status"
        ),
        "verification_results": verification,
        "execution_trace": trace,
        "evidence": evidence,
        "deliverables": deliverables,
    }
)