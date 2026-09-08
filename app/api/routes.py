from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.state.workflow_state import WorkflowState
from app.services.conversation_service import ConversationService
from app.workflow.graph import WorkflowGraph
from app.workflow.nodes.input_processor import (
    detect_input_modalities,
    prepare_uploaded_files,
)

router = APIRouter()
logger = get_logger("api.routes")
analysis_store: dict[str, dict] = {}
conversation_service = ConversationService()


def run_multimodal_analysis(
    user_query: str,
    files: list[UploadFile],
    requested_deliverable: str | None = None,
    conversation_id: str | None = None,
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

    if conversation_id is None:
        conversation_id = conversation_service.create_conversation()
    elif not conversation_service.exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    conversation_history = conversation_service.get_history(
        conversation_id
    )

    state = WorkflowState(
        request_id=request_id,
        conversation_id=conversation_id,
        conversation_history=conversation_history,
        input_types=input_types,
        user_query=user_query,
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

    workflow_builder = WorkflowGraph()

    workflow = workflow_builder.build()

    final_state = workflow.invoke(state)

    # LangGraph should return WorkflowState, but allow
    # dictionary output as a defensive fallback.
    if isinstance(final_state, WorkflowState):
        result = final_state
    else:
        result = WorkflowState.model_validate(final_state)


    conversation_service.add_message(
        result.conversation_id,
        "user",
        user_query,
    )

    if result.final_answer:
        conversation_service.add_message(
            result.conversation_id,
            "assistant",
            result.final_answer,
        )

    # ---------------------------------------------------------
    # API RESPONSE
    # ---------------------------------------------------------

    response = {
            "request_id": result.request_id,
            "conversation_id": result.conversation_id,
            "status": "completed",
            "final_answer": result.final_answer,
            "evidence": [
                *result.retrieved_evidence,
                *result.data_results,
                *result.vision_results,
            ],
            "verification_status": result.verification_status,
            "verification_results": result.verification_results,
            "traceability": result.execution_trace,
            "execution_telemetry": result.execution_telemetry,
            "generated_deliverables": result.generated_deliverables,
    }

    analysis_store[result.request_id] = response

    return response


@router.post("/analyze")
async def analyze(
    user_query: str = Form(...),
    conversation_id: str | None = Form(None),
    requested_deliverable: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
):
    return run_multimodal_analysis(
        user_query=user_query,
        files=files,
        requested_deliverable=requested_deliverable,
        conversation_id=conversation_id,
    )


@router.get("/analysis/{request_id}")
async def get_analysis_status(request_id: str):
    result = analysis_store.get(request_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    return {
        "request_id": result["request_id"],
        "status": result["status"],
        "verification_status": result["verification_status"],
        "final_answer": result["final_answer"],
        "generated_deliverables": result["generated_deliverables"],
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