from __future__ import annotations

from dataclasses import asdict
from app.state.execution_trace_projection import project_execution_trace
from app.hitl.manager import (
    ApprovalManager,
    ApprovalNotFoundError,
    ApprovalTransitionError,
)
from app.api.schemas import ReportCreateRequest
from app.report.service import ReportService

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.state.workflow_state import WorkflowState
from app.state.manager import AgentStateManager
from app.services.conversation_service import ConversationService
from app.services.knowledge_vault import KnowledgeVault
from app.workflow.graph import WorkflowGraph
from app.workflow.nodes.input_processor import (
    detect_input_modalities,
    prepare_uploaded_files,
)

router = APIRouter()
logger = get_logger("api.routes")
analysis_store: dict[str, dict] = {}
approval_manager = ApprovalManager()
conversation_service = ConversationService()
knowledge_vault = KnowledgeVault()
state_manager = AgentStateManager()
report_service = ReportService(state_manager=state_manager)


def build_analysis_error(
    *,
    run_id: str,
    stage: str = "ANALYZING",
    error_code: str = "ANALYSIS_EXECUTION_FAILED",
    user_message: str = "Analysis could not be completed.",
    retryable: bool = True,
    recovery_action: str = "Retry the analysis.",
) -> dict:
    return {
        "error_code": error_code,
        "classification": "RETRYABLE" if retryable else "PERMANENT",
        "user_message": user_message,
        "retryable": retryable,
        "recovery_action": recovery_action,
        "run_id": run_id,
        "stage": stage,
    }

@router.get("/approvals/{approval_id}")
def get_approval(approval_id: str) -> dict:
    try:
        approval = approval_manager.get_request(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found.",
        )

    return approval.to_dict()


@router.get("/tasks/{task_id}/approvals")
def list_task_approvals(task_id: str) -> dict:
    try:
        state_manager.require_task(task_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    approvals = approval_manager.list_pending(task_id=task_id)

    return {
        "task_id": task_id,
        "approvals": [approval.to_dict() for approval in approvals],
    }


@router.post("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str) -> dict:
    try:
        approval = approval_manager.approve(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found.",
        )
    except ApprovalTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return approval.to_dict()


@router.post("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str) -> dict:
    try:
        approval = approval_manager.reject(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found.",
        )
    except ApprovalTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return approval.to_dict()


@router.post("/approvals/{approval_id}/cancel")
def cancel_approval(approval_id: str) -> dict:
    try:
        approval = approval_manager.cancel(approval_id)
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found.",
        )
    except ApprovalTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return approval.to_dict()

def run_multimodal_analysis(
    user_query: str,
    files: list[UploadFile],
    requested_deliverable: str | None = None,
    conversation_id: str | None = None,
    task_id: str | None = None,
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
    task_id = task_id or f"task_{uuid.uuid4().hex}"

    state_manager.create_task(
        task_id=task_id,
        goal=user_query,
    )
    state_manager.add_step(
        task_id=task_id,
        step_id="workflow_execution",
    )
    state_manager.start_task(task_id)
    state_manager.start_step(
        task_id=task_id,
        step_id="workflow_execution",
    )
    state_manager.update_run_metadata(
        task_id,
        run_id=task_id,
        updates={
            "request_id": request_id,
        },
    )

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
        task_id=task_id,
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

    try:
        final_state = workflow.invoke(state)
    except Exception as exc:
        error = build_analysis_error(
            run_id=task_id,
            stage="ANALYZING",
        )
        state_manager.fail_step(
            task_id,
            "workflow_execution",
            "Analysis workflow execution failed",
        )
        state_manager.update_metadata(
            task_id,
            {
                "error": error,
                "result": {
                    "request_id": request_id,
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "status": "failed",
                    "final_answer": None,
                    "evidence": [],
                    "verification_status": None,
                    "verification_results": [],
                    "stages": [],
                    "execution_events": [],
                    "generated_deliverables": [],
                    "error": error,
                },
            },
        )
        state_manager.fail_task(task_id)
        logger.exception("Analysis workflow execution failed")
        raise

    # LangGraph should return WorkflowState, but allow
    # dictionary output as a defensive fallback.
    if isinstance(final_state, WorkflowState):
        result = final_state
    else:
        result = WorkflowState.model_validate(final_state)

    state_manager.complete_step(
        task_id,
        "workflow_execution",
        result={
            "verification_status": result.verification_status,
            "generated_deliverables": result.generated_deliverables,
        },
    )

    state_manager.complete_task(task_id)

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
            "task_id": result.task_id,
            "conversation_id": result.conversation_id,
            "status": "completed",
            "final_answer": result.final_answer,
            "evidence": [
                *result.retrieved_evidence,
                *result.data_results,
                *result.code_results,
                *result.vision_results,
            ],
            "verification_status": result.verification_status,
            "verification_results": result.verification_results,
            "stages": [
                asdict(stage)
                for stage in project_execution_trace(
                    run_id=task_id,
                    execution_trace=result.execution_trace,
                    )
            ],
            "execution_events": result.execution_events,
            "traceability": result.execution_trace,
            "execution_telemetry": result.execution_telemetry,
            "generated_deliverables": result.generated_deliverables,
    }

    state_manager.update_metadata(
        task_id,
        {
            "result": {
                "request_id": response["request_id"],
                "task_id": response["task_id"],
                "conversation_id": response["conversation_id"],
                "status": response["status"],
                "final_answer": response["final_answer"],
                "evidence": response["evidence"],
                "verification_status": response["verification_status"],
                "verification_results": response["verification_results"],
                "stages": response["stages"],
                "execution_events": response["execution_events"],
                "generated_deliverables": response["generated_deliverables"],
            },
        },
    )

    analysis_store[result.request_id] = response

    return response

@router.post("/tasks/{task_id}/reports")
def create_task_report(
    task_id: str,
    request: ReportCreateRequest,
) -> dict:
    try:
        report = report_service.create_report(
            task_id=task_id,
            title=request.title,
            subtitle=request.subtitle,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return report.model_dump(mode="json")

@router.get("/reports/{report_id}")
def get_report(report_id: str) -> dict:
    report = report_service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return report.model_dump(mode="json")

@router.get("/tasks/{task_id}/reports")
def list_task_reports(task_id: str) -> dict:
    try:
        reports = report_service.list_reports(task_id=task_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return {
        "task_id": task_id,
        "reports": [
            report.model_dump(mode="json")
            for report in reports
        ],
    }

@router.get("/tasks/{task_id}")
def get_task_status(task_id: str) -> dict:
    try:
        task = state_manager.require_task(task_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "current_step_id": task.current_step_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "version": task.version,
    }

@router.post("/analyze/stream")
async def analyze_stream(
    user_query: str = Form(...),
    files: list[UploadFile] | None = File(default=None),
    requested_deliverable: str | None = Form(default=None),
    conversation_id: str | None = Form(default=None),
    task_id: str | None = Form(default=None),
):
    task_id = task_id or f"task_{uuid.uuid4().hex}"

    existing_task = state_manager.get_task(task_id)

    if existing_task is not None:
        durable_result = existing_task.metadata.get("result")

        if durable_result is not None:
            async def replay_stream():
                import json

                def sse(event: str, data: dict) -> str:
                    return (
                        f"event: {event}\\n"
                        f"data: {json.dumps(data, default=str)}\\n\\n"
                    )

                yield sse(
                    "workflow",
                    {
                        "event_id": f"{task_id}_1",
                        "run_id": task_id,
                        "sequence": 1,
                        "status": "started",
                        "message": "Analysis recovered",
                    },
                )

                yield sse(
                    "workflow",
                    {
                        "event_id": f"{task_id}_2",
                        "run_id": task_id,
                        "sequence": 2,
                        "status": "processing",
                        "message": "Recovered analysis state",
                    },
                )

                if durable_result.get("status") == "failed":
                    yield sse(
                        "error",
                        {
                            "event_id": f"{task_id}_3",
                            "run_id": task_id,
                            "sequence": 3,
                            "status": "failed",
                            "error": durable_result.get(
                                "error",
                                build_analysis_error(
                                    run_id=task_id,
                                    stage="ANALYZING",
                                ),
                            ),
                        },
                    )
                else:
                    yield sse(
                        "completed",
                        {
                            "event_id": f"{task_id}_3",
                            "run_id": task_id,
                            "sequence": 3,
                            "request_id": durable_result.get(
                                "request_id"
                            ),
                            "conversation_id": durable_result.get(
                                "conversation_id"
                            ),
                            "status": durable_result.get("status"),
                            "final_answer": durable_result.get(
                                "final_answer"
                            ),
                            "evidence": durable_result.get(
                                "evidence",
                                [],
                            ),
                            "verification_status": durable_result.get(
                                "verification_status"
                            ),
                            "verification_results": durable_result.get(
                                "verification_results",
                                [],
                            ),
                            "generated_deliverables": durable_result.get(
                                "generated_deliverables",
                                [],
                            ),
                            "stages": durable_result.get(
                                "stages",
                                [],
                            ),
                            "execution_events": durable_result.get(
                                "execution_events",
                                [],
                            ),
                        },
                    )

            return StreamingResponse(
                replay_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        async def reconnect_stream():
            import json

            def sse(event: str, data: dict) -> str:
                return (
                    f"event: {event}\\n"
                    f"data: {json.dumps(data, default=str)}\\n\\n"
                )

            status = existing_task.status.value

            yield sse(
                "workflow",
                {
                    "event_id": f"{task_id}_1",
                    "run_id": task_id,
                    "sequence": 1,
                    "status": status.lower(),
                    "message": "Analysis state recovered",
                },
            )

            if status == "CANCELLED":
                yield sse(
                    "error",
                    {
                        "event_id": f"{task_id}_2",
                        "run_id": task_id,
                        "sequence": 2,
                        "status": "cancelled",
                        "error": {
                            "error_code": "ANALYSIS_CANCELLED",
                            "classification": "CANCELLED",
                            "user_message": "Analysis was cancelled.",
                            "retryable": False,
                            "recovery_action": "Start a new analysis if needed.",
                            "run_id": task_id,
                            "stage": "ANALYZING",
                        },
                    },
                )
                return

            if status in {"COMPLETED", "FAILED"}:
                yield sse(
                    "error" if status == "FAILED" else "completed",
                    {
                        "event_id": f"{task_id}_2",
                        "run_id": task_id,
                        "sequence": 2,
                        "status": status.lower(),
                        "message": "Analysis reached a terminal state without a durable result.",
                    },
                )
                return

            yield sse(
                "workflow",
                {
                    "event_id": f"{task_id}_2",
                    "run_id": task_id,
                    "sequence": 2,
                    "status": status.lower(),
                    "message": "Analysis is already in progress.",
                },
            )

        return StreamingResponse(
            reconnect_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_stream():
        def sse(event: str, data: dict) -> str:
            import json

            return (
                f"event: {event}\n"
                f"data: {json.dumps(data, default=str)}\n\n"
            )

        yield sse(
            "workflow",
            {
                "event_id": f"{task_id}_1",
                "run_id": task_id,
                "sequence": 1,
                "status": "started",
                "message": "Analysis started",
            },
        )

        yield sse(
            "workflow",
            {
                "event_id": f"{task_id}_2",
                "run_id": task_id,
                "sequence": 2,
                "status": "processing",
                "message": "Running verified workflow",
            },
        )

        try:
            result = await asyncio.to_thread(
                run_multimodal_analysis,
                user_query=user_query,
                files=files,
                requested_deliverable=requested_deliverable,
                conversation_id=conversation_id,
                task_id=task_id,
            )

            yield sse(
                "completed",
                {
                    "event_id": f"{task_id}_3",
                    "run_id": task_id,
                    "sequence": 3,
                    "request_id": result.get("request_id"),
                    "conversation_id": result.get("conversation_id"),
                    "status": result.get("status"),
                    "final_answer": result.get("final_answer"),
                    "evidence": result.get("evidence", []),
                    "verification_status": result.get("verification_status"),
                    "verification_results": result.get(
                        "verification_results", []
                    ),
                    "generated_deliverables": result.get(
                        "generated_deliverables", []
                    ),
                    "stages": result.get("stages", []),
                    "execution_events": result.get("execution_events", []),
                },
            )

        except Exception:
            logger.exception("Streaming analysis failed")

            yield sse(
                "error",
                {
                    "event_id": f"{task_id}_3",
                    "run_id": task_id,
                    "sequence": 3,
                    "status": "failed",
                    "error": build_analysis_error(
                        run_id=task_id,
                        stage="ANALYZING",
                    ),
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

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
        task = state_manager.find_task_by_metadata(
            "request_id",
            request_id,
        )

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found",
            )

        result = task.metadata.get("result")

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Analysis result not available",
            )

    response = {
        "request_id": result["request_id"],
        "status": result["status"],
        "verification_status": result["verification_status"],
        "final_answer": result["final_answer"],
        "generated_deliverables": result["generated_deliverables"],
    }

    if result.get("error") is not None:
        response["error"] = result["error"]

    return response


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

@router.post("/vault/upload")
async def upload_to_vault(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported",
        )

    upload_dir = Path.cwd() / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    temporary_path = upload_dir / filename

    contents = await file.read()
    temporary_path.write_bytes(contents)

    file_type = extension.lstrip(".")

    try:
        result = knowledge_vault.add_document(
            file_path=temporary_path,
            file_type=file_type,
        )
    except Exception as exc:
        logger.exception("Vault ingestion failed")
        raise HTTPException(
            status_code=500,
            detail='Vault ingestion failed',
        ) from exc

    return result

@router.get("/vault/documents")
async def list_vault_documents():
    return {
        "documents": knowledge_vault.list_documents()
    }

@router.get("/vault/documents/{document_id}")
async def get_vault_document(document_id: str):
    document = knowledge_vault.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Vault document not found",
        )

    return document

@router.delete("/vault/documents/{document_id}")
async def delete_vault_document(document_id: str):
    deleted = knowledge_vault.delete_document(document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Vault document not found",
        )

    return {
        "document_id": document_id,
        "deleted": True,
    }

@router.post("/vault/documents/{document_id}/reindex")
async def reindex_vault_document(document_id: str):
    try:
        return knowledge_vault.reindex_document(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail='Vault document source not found',
        ) from exc
    except Exception as exc:
        logger.exception("Vault re-indexing failed")
        raise HTTPException(
            status_code=500,
            detail="Vault re-indexing failed",
        ) from exc

@router.get("/vault/search")
async def search_vault(
    query: str,
    top_k: int = 5,
):
    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query is required",
        )

    results = knowledge_vault.search(
        query=query,
        top_k=top_k,
    )

    return {
        "query": query,
        "results": [
            {
                "evidence_id": item.evidence_id,
                "source_file_id": item.source_file_id,
                "source_filename": item.source_filename,
                "page_number": item.page_number,
                "chunk_id": item.chunk_id,
                "text": item.text,
                "relevance_score": item.relevance_score,
                "retrieval_method": item.retrieval_method,
            }
            for item in results
        ],
    }
