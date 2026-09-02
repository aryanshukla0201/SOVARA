from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.state.workflow_state import WorkflowState
from app.workflow.graph import WorkflowGraph
from app.workflow.nodes.input_processor import (
    detect_input_modalities,
    prepare_uploaded_files,
)

router = APIRouter()
logger = get_logger("api.routes")


def run_multimodal_analysis(
    user_query: str,
    files: list[UploadFile],
    requested_deliverable: str = "report",
) -> dict:
    """
    API adapter for the SOVARA workflow.

    Responsibilities:
    1. Save uploaded files.
    2. Create the initial WorkflowState.
    3. Execute the LangGraph workflow.
    4. Convert the final state into an API response.
    """

    request_id = f"req_{uuid.uuid4().hex[:8]}"

    settings = get_settings()
    workspace_root = Path.cwd()

    upload_dir = workspace_root / settings.upload_directory
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []

    # ---------------------------------------------------------
    # SAVE UPLOADED FILES
    # ---------------------------------------------------------

    for uploaded_file in files:
        if not uploaded_file.filename:
            continue

        filename = Path(uploaded_file.filename).name
        destination = upload_dir / filename

        contents = uploaded_file.file.read()
        destination.write_bytes(contents)

        saved_paths.append(destination)

    # ---------------------------------------------------------
    # INITIAL WORKFLOW STATE
    # ---------------------------------------------------------

    input_types = detect_input_modalities(
        user_query,
        saved_paths,
    )

    state = WorkflowState(
        request_id=request_id,
        user_query=user_query,
        input_types=input_types,
        requested_deliverable=requested_deliverable,
    )

    state.uploaded_files = prepare_uploaded_files(
        user_query,
        saved_paths,
        base_dir=str(upload_dir),
    )

    # ---------------------------------------------------------
    # RUN ACTUAL SOVARA LANGGRAPH WORKFLOW
    # ---------------------------------------------------------

    workflow = WorkflowGraph().build()

    final_state = workflow.invoke(state)

    # LangGraph should return WorkflowState, but allow
    # dictionary output as a defensive fallback.
    if isinstance(final_state, WorkflowState):
        result = final_state
    else:
        result = WorkflowState.model_validate(final_state)

    # ---------------------------------------------------------
    # API RESPONSE
    # ---------------------------------------------------------

    return {
        "request_id": result.request_id,
        "status": "completed",
        "final_answer": result.final_answer,
        "evidence": result.retrieved_evidence,
        "verification_status": result.verification_status,
        "traceability": result.execution_trace,
        "generated_deliverables": result.generated_deliverables,
    }


@router.post("/analyze")
async def analyze(
    user_query: str = Form(...),
    requested_deliverable: str = Form("report"),
    files: list[UploadFile] = File(default=[]),
):
    return run_multimodal_analysis(
        user_query=user_query,
        files=files,
        requested_deliverable=requested_deliverable,
    )


@router.get("/analysis/{request_id}")
async def get_analysis_status(request_id: str):
    return {
        "request_id": request_id,
        "status": "completed",
        "final_answer": (
            "Analysis complete. "
            "Run /download to fetch the deliverable."
        ),
    }


@router.get("/download/{request_id}/{file_name}")
async def download_file(
    request_id: str,
    file_name: str,
):
    settings = get_settings()

    safe_filename = Path(file_name).name
    path = (
        Path.cwd()
        / settings.output_directory
        / safe_filename
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return FileResponse(path=path)