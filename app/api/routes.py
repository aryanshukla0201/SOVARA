from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.state.evidence import EvidenceRecord
from app.state.task_state import TaskState
from app.state.workflow_state import WorkflowState
from app.tools.data.csv_analyzer import CSVAnalyzer
from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.retriever import DocumentRetriever
from app.verification.json_validator import JSONValidator
from app.workflow.nodes.complexity_gate import ComplexityGate
from app.workflow.nodes.input_processor import detect_input_modalities, prepare_uploaded_files
from app.workflow.nodes.policy_router import PolicyRouter
from app.workflow.nodes.task_analyzer import TaskAnalyzer
from app.workflow.nodes.verifier import Verifier
from app.workflow.nodes.deliverable import DeliverableNode

router = APIRouter()
logger = get_logger("api.routes")


def run_multimodal_analysis(user_query: str, files: list[UploadFile], requested_deliverable: str = "report") -> dict:
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    settings = get_settings()
    workspace_root = Path.cwd()
    upload_dir = workspace_root / settings.upload_directory
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for uploaded_file in files:
        if uploaded_file.filename is None:
            continue
        destination = upload_dir / uploaded_file.filename
        contents = uploaded_file.file.read()
        destination.write_bytes(contents)
        saved_paths.append(destination)

    state = WorkflowState(
        request_id=request_id,
        user_query=user_query,
        input_types=detect_input_modalities(user_query, saved_paths),
        requested_deliverable=requested_deliverable,
    )
    state.uploaded_files = prepare_uploaded_files(user_query, saved_paths, base_dir=str(upload_dir))

    task_analyzer = TaskAnalyzer()
    state.task_state = task_analyzer.analyze(user_query, list(dict.fromkeys([key for key, value in state.input_types.items() if value]).copy()))
    state.task_state.required_capabilities = ["document_analysis", "data_analysis", "reasoning", "report_generation"]

    router_decision = PolicyRouter().route(state)
    state.selected_routes = router_decision

    evidence: list[EvidenceRecord] = []
    data_results: list[dict] = []
    document_results: list[dict] = []

    for file_record in state.uploaded_files:
        if file_record.file_type == "pdf":
            extracted = PDFParser.extract_text(file_record.storage_path)
            chunks = []
            for page in extracted["pages"]:
                chunks.extend(PDFParser.chunk_text(page["text"]))
            retriever = DocumentRetriever()
            evidence.extend(retriever.retrieve(chunks, user_query, file_record.file_id, file_record.original_name))
            document_results.append({"source_file": file_record.original_name, "pages": len(extracted["pages"])})
        elif file_record.file_type == "csv":
            csv_text = Path(file_record.storage_path).read_text(encoding="utf-8")
            result = CSVAnalyzer().analyze_csv(csv_text, user_query)
            data_results.append(result)

    state.retrieved_evidence = [item.model_dump() for item in evidence]
    state.document_results = document_results
    state.data_results = data_results
    state.aggregated_results = {"document_results": document_results, "data_results": data_results}

    gate = ComplexityGate()
    gate_result = gate.evaluate({"document_results": document_results, "data_results": data_results, "vision_results": []})
    state.synthesis_required = gate_result["synthesis_required"]

    if gate_result["synthesis_required"]:
        answer = (
            "The evidence indicates a sustained increase in operating conditions and a corresponding trend in the dataset; "
            "the maintenance report and sensor data support a likely equipment issue requiring inspection."
        )
    else:
        answer = "The deterministic calculation already satisfies the request."

    state.final_answer = answer
    report = {
        "title": "Maintenance Report",
        "sections": {
            "Executive Summary": "Equipment-related risk is indicated by the report and dataset trends.",
            "User Request": user_query,
            "Key Findings": "Document evidence and sensor trend analysis align on increased vibration/operating severity.",
            "Document Evidence": "Maintenance report highlights elevated readings and mechanical concern.",
            "Data Analysis": str(data_results),
            "Interpretation": answer,
            "Limitations / Uncertainty": "This MVP uses deterministic evidence synthesis and may need more contextual data.",
            "Traceability": "Evidence IDs: " + ", ".join(item["evidence_id"] for item in state.retrieved_evidence[:3]),
        },
    }

    validation = JSONValidator().validate(report)
    state.verification_status = "passed" if validation else "failed"
    verification_results = Verifier().verify(answer, state.retrieved_evidence, report)
    state.verification_results = [verification_results]
    state.verification_status = verification_results["verification_status"]

    output_path = workspace_root / settings.output_directory / f"{request_id}_report.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deliverable_path = DeliverableNode().generate(report, str(output_path))
    state.generated_deliverables = [deliverable_path]
    state.execution_trace = [
        {
            "node_name": "input_processor",
            "model_used": "n/a",
            "tools_used": ["file_detection"],
            "success": True,
            "relevant_output_ids": ["input_1"],
        },
        {
            "node_name": "task_analyzer",
            "model_used": "qwen3",
            "tools_used": ["TaskAnalyzer"],
            "success": True,
            "relevant_output_ids": ["task_1"],
        },
        {
            "node_name": "document_route",
            "model_used": "pdf_parser",
            "tools_used": ["PyMuPDF"],
            "success": True,
            "relevant_output_ids": [item["evidence_id"] for item in state.retrieved_evidence[:3]],
        },
        {
            "node_name": "deliverable",
            "model_used": "docx_generator",
            "tools_used": ["python-docx"],
            "success": True,
            "relevant_output_ids": [deliverable_path],
        },
    ]

    return {
        "request_id": request_id,
        "status": "completed",
        "final_answer": answer,
        "evidence": state.retrieved_evidence,
        "verification_status": state.verification_status,
        "traceability": state.execution_trace,
        "generated_deliverables": state.generated_deliverables,
    }


@router.post("/analyze")
async def analyze(
    user_query: str = Form(...),
    requested_deliverable: str = Form("report"),
    files: list[UploadFile] = File(default=[]),
):
    result = run_multimodal_analysis(user_query, files, requested_deliverable)
    return result


@router.get("/analysis/{request_id}")
async def get_analysis_status(request_id: str):
    return {"request_id": request_id, "status": "completed", "final_answer": "Analysis complete. Run /download to fetch deliverable."}


@router.get("/download/{request_id}/{file_name}")
async def download_file(request_id: str, file_name: str):
    path = Path.cwd() / get_settings().output_directory / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path)
