from __future__ import annotations

import re

from pathlib import Path

from langgraph.graph import END, StateGraph

from app.state.workflow_state import WorkflowState
from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.retriever import DocumentRetriever
from app.tools.vision.image_analyzer import VisionAnalyzer
from app.workflow.nodes.complexity_gate import ComplexityGate
from app.workflow.nodes.data_node import DataNode
from app.workflow.nodes.deliverable import DeliverableNode
from app.workflow.nodes.document_node import DocumentNode
from app.workflow.nodes.document_fact_extractor import (
    DocumentFactExtractor,
)
from app.workflow.nodes.code_execution_node import CodeExecutionNode
from app.workflow.nodes.code_pipeline import CodePipeline
from app.workflow.nodes.code_agent import CodeAgent
from app.workflow.nodes.input_processor import detect_input_modalities
from app.workflow.nodes.policy_router import PolicyRouter
from app.services.evidence_normalizer import EvidenceNormalizer
from app.workflow.nodes.reasoning_node import ReasoningNode
from app.workflow.nodes.repair import RepairNode
from app.workflow.nodes.synthesis import SynthesisNode
from app.workflow.nodes.task_analyzer import TaskAnalyzer
from app.workflow.nodes.vision_node import VisionNode
from app.workflow.nodes.verifier import Verifier
from app.services.execution_telemetry import ExecutionTelemetry
from app.services.knowledge_vault import KnowledgeVault


class WorkflowGraph:
    def __init__(self):
        self.graph = StateGraph(WorkflowState)
        self.max_repair_attempts = 3

        # Request execution telemetry
        self.telemetry = ExecutionTelemetry()

        self.retriever = DocumentRetriever()
        self.knowledge_vault = KnowledgeVault(
            retriever=self.retriever
        )

    def _trace(
        self,
        state: WorkflowState,
        node_name: str,
        model_used: str = "n/a",
        tools_used: list[str] | None = None,
        success: bool = True,
        relevant_output_ids: list[str] | None = None,
    ) -> None:
        state.execution_trace.append(
            {
                "node_name": node_name,
                "model_used": model_used,
                "tools_used": tools_used or [],
                "success": success,
                "relevant_output_ids": relevant_output_ids or [],
            }
        )

    @staticmethod
    def _model_name(model) -> str:
        if model is None:
            return "n/a"

        return getattr(
            model,
            "model_name",
            getattr(model, "name", "unknown"),
        )

    def _input_processor(self, state: WorkflowState) -> WorkflowState:
        if state.user_query:
            state.input_types = detect_input_modalities(state.user_query, [file.storage_path for file in state.uploaded_files])
        if not state.uploaded_files and state.input_metadata:
            state.input_types = detect_input_modalities(state.user_query, list(state.input_metadata.get("paths", [])))

        self._trace(
            state,
            node_name="input_processor",
            model_used="n/a",
            tools_used=["file_detection"],
            relevant_output_ids=[
                f"input_{len(state.uploaded_files)}"
            ],
        )
        return state

    def _task_analyzer(self, state: WorkflowState) -> WorkflowState:
        input_types = list(dict.fromkeys([key for key, value in state.input_types.items() if value]))
        task_analyzer = TaskAnalyzer(
            telemetry=self.telemetry,
        )

        state.task_state = task_analyzer.analyze(
            state.user_query,
            input_types,
        )

        self._trace(
            state,
            node_name="task_analyzer",
            model_used=self._model_name(task_analyzer.model),
            tools_used=["TaskAnalyzer"],
            relevant_output_ids=["task_1"],
        )
        return state

    def _policy_router(self, state: WorkflowState) -> WorkflowState:
        state.selected_routes = PolicyRouter().route(state)

        # Enforce deterministic execution order.
        # Evidence-producing routes must run before reasoning,
        # because reasoning should have access to all available evidence.
        route_priority = {
            "document": 1,
            "data": 2,
            "vision": 3,
            "code_execution": 4,
            "reasoning": 5,
        }

        state.selected_routes.sort(
            key=lambda route: route_priority.get(route, 99)
        )

        state.pending_routes = list(state.selected_routes)
        state.completed_routes = []
        state.current_route = ""

        self._trace(
            state,
            node_name="policy_router",
            model_used="n/a",
            tools_used=["PolicyRouter"],
            relevant_output_ids=list(state.selected_routes),
        )

        return state
    def _vault_route(self, state: WorkflowState) -> WorkflowState:
        evidence = self.knowledge_vault.search(
            query=state.user_query,
            top_k=5,
        )

        state.retrieved_evidence = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in evidence
        ]
        self.telemetry.record_tool("KnowledgeVault")
        return state

    def _should_use_document_fact_extraction(
        self,
        state: WorkflowState,
    ) -> str:
        field = DocumentFactExtractor.detect_field(
            state.user_query
        )

        if (
            field
            and state.retrieved_evidence
            and any(
                isinstance(item, dict)
                and item.get("content")
                for item in state.retrieved_evidence
            )
        ):
            return "document_fact"

        return "reasoning"

    def _document_route(self, state: WorkflowState) -> WorkflowState:
        document_node = DocumentNode(
            retriever=self.knowledge_vault.retriever
        )

        self.telemetry.record_tool("DocumentNode")

        for file_record in state.uploaded_files:
            if file_record.file_type not in {"pdf", "docx"}:
                continue

            self.telemetry.record_file()

            evidence = document_node.run(
                file_record.storage_path,
                state.user_query,
                file_record.file_id,
                file_record.file_type,
            )

            self.telemetry.record_tool("DocumentRetriever")

            state.retrieved_evidence.extend(
                [item.model_dump() for item in evidence]
            )

            if file_record.file_type == "pdf":
                pages = len(
                    PDFParser.extract_text(
                        file_record.storage_path
                    ).get("pages", [])
                )
            else:
                pages = None

            state.document_results.append({
                "source_file": file_record.original_name,
                "file_id": file_record.file_id,
                "file_type": file_record.file_type,
                "pages": pages,
                "evidence_count": len(evidence),
            })

        return state

    def _data_route(self, state: WorkflowState) -> WorkflowState:
        data_node = DataNode()
        self.telemetry.record_tool("DataNode")

        for file_record in state.uploaded_files:

            if file_record.file_type not in {"csv", "xlsx"}:
                continue

            self.telemetry.record_file()

            if file_record.file_type == "csv":
                with open(
                    file_record.storage_path,
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as handle:
                    source = handle.read()

            else:
                source = file_record.storage_path

            result = data_node.run(
                source=source,
                file_type=file_record.file_type,
                user_query=state.user_query,
            )

            self.telemetry.record_tool(result["tool_used"])

            state.data_results.append(
                {
                **result,
                "source_file": file_record.original_name,
                "file_id": file_record.file_id,
                }
            )

            self._trace(
            state,
            node_name="data_route",
            model_used="n/a",
            tools_used=["DataNode"],
            relevant_output_ids=[
                item["file_id"]
                for item in state.data_results
            ],
        )
        return state

    def _vision_route(self, state: WorkflowState) -> WorkflowState:
        for file_record in state.uploaded_files:
            if file_record.file_type != "image":
                continue

            if self.telemetry is not None:
                self.telemetry.record_file()
                self.telemetry.record_tool("VisionAnalyzer")
            vision_node = VisionNode(
                telemetry=self.telemetry
            )

            try:


                result = vision_node.run(


                    file_record.storage_path,


                    state.user_query


                )


            except Exception as exc:


                error_message = (


                    f"Unable to analyze image "


                    f"'{file_record.original_name}': {exc}"


                )



                state.vision_results.append({


                    "source_file": file_record.original_name,


                    "file_id": file_record.file_id,


                    "result": {


                        "error": error_message,


                    },


                })



                state.retrieved_evidence.append({


                    "evidence_id": f"{file_record.file_id}_error",


                    "source_file_id": file_record.file_id,


                    "source_filename": file_record.original_name,


                    "evidence_type": "vision",


                    "content": error_message,


                    "confidence": 1.0,


                    "retrieval_method": "vision_error",


                })



                self._trace(


                    state,


                    node_name="vision_route",


                    model_used=self._model_name(


                        getattr(vision_node.analyzer, "analyzer", None)


                    ),


                    tools_used=["VisionAnalyzer"],


                    relevant_output_ids=[


                        f"{file_record.file_id}_error"


                    ],


                )



                continue

            vision_model = (
                result.get("model")
                if isinstance(result, dict)
                else None
            )

            if vision_model and self.telemetry is not None:
                self.telemetry.record_llm_call(
                    vision_model,
                    local=True,
                )

            # Keep the complete vision result for multimodal reasoning
            state.vision_results.append({
                "source_file": file_record.original_name,
                "file_id": file_record.file_id,
                "result": result,
            })

            # Convert each visual observation into citation-valid evidence
            observations = result.get("observations", [])

            for index, observation in enumerate(observations, start=1):
                state.retrieved_evidence.append({
                    "evidence_id": f"{file_record.file_id}_ev_{index:03d}",
                    "source_file_id": file_record.file_id,
                    "source_filename": file_record.original_name,
                    "evidence_type": "vision",
                    "content": observation.get("description", ""),
                    "confidence": observation.get("confidence"),
                    "retrieval_method": "vision_model",
                })

            self._trace(
                state,
                node_name="vision_route",
                model_used=(
                    vision_model
                    or self._model_name(vision_node.analyzer)
                ),
                tools_used=["VisionAnalyzer"],
                relevant_output_ids=[
                    f"{file_record.file_id}_ev_{index:03d}"
                    for index in range(1, len(observations) + 1)
                ],
            )

        return state
    def _code_execution(self, state: WorkflowState) -> WorkflowState:
        self.telemetry.record_tool("CodePipeline")

        input_files = [
            file.storage_path
            for file in state.uploaded_files
            if file.storage_path
        ]

        code_pipeline = CodePipeline(
            telemetry=self.telemetry,
        )
        result = code_pipeline.run(
            user_query=state.user_query,
            input_files=input_files,
        )

        state.code_results.append(result)

        self._trace(
            state,
            node_name="code_execution",
            model_used=self._model_name(code_pipeline.agent.model),
            tools_used=[
                "CodePipeline",
                "CodeAgent",
                "CodeSandbox",
            ],
            relevant_output_ids=[result["evidence_id"]],
            success=result.get("success", False),
        )

        return state

    def _document_fact_route(
        self,
        state: WorkflowState,
    ) -> WorkflowState:
        result = DocumentFactExtractor.extract(
            query=state.user_query,
            evidence=evidence,
        )

        if result.success:
            state.document_fact_results.append(
                {
                    "answer": result.answer,
                    "evidence_id": result.evidence_id,
                    "field": result.field,
                    "method": "deterministic_document_fact_extraction",
                }
            )

            self._trace(
                state,
                node_name="document_fact_extraction",
                model_used="n/a",
                tools_used=["DocumentFactExtractor"],
                relevant_output_ids=[
                    result.evidence_id
                ]
                if result.evidence_id
                else [],
            )

        return state

    def _reasoning_route(self, state: WorkflowState) -> WorkflowState:
        self.telemetry.record_tool("ReasoningNode")

        task_state = state.task_state

        if (
            task_state
            and "project_context" in task_state.required_capabilities
            and not state.uploaded_files
        ):
            readme_path = Path("README.md")

            if readme_path.exists():
                content = readme_path.read_text(
                    encoding="utf-8",
                ).strip()

                if content and not any(
                    item.get("evidence_id") == "project_sovara_readme"
                    for item in state.retrieved_evidence
                    if isinstance(item, dict)
                ):
                    state.retrieved_evidence.insert(
                        0,
                        {
                            "evidence_id": "project_sovara_readme",
                            "evidence_type": "project_context",
                            "source_filename": "README.md",
                            "content": content,
                        },
                    )

        evidence = state.retrieved_evidence

        reasoning_node = ReasoningNode(
            telemetry=self.telemetry,
        )

        result = reasoning_node.run(
            user_query=state.user_query,
            evidence=evidence,
            data_results=state.data_results,
            code_results=state.code_results,
            vision_results=state.vision_results,
            conversation_history=state.conversation_history,
        )

        state.reasoning_results.append(result)

        self._trace(
            state,
            node_name="reasoning_route",
            model_used=self._model_name(reasoning_node.model),
            tools_used=["ReasoningNode"],
            relevant_output_ids=[
                f"reasoning_{len(state.reasoning_results)}"
            ],
        )

        return state

    def _execution_dispatch(self, state: WorkflowState) -> WorkflowState:
        if not state.pending_routes:
            state.current_route = ""
            return state

        state.current_route = state.pending_routes[0]
        state.pending_routes = state.pending_routes[1:]

        # For simple exact document facts, replace the LLM
        # reasoning route with deterministic extraction.
        if (
            state.current_route == "reasoning"
            and state.retrieved_evidence
            and DocumentFactExtractor.detect_field(state.user_query) is not None
        ):
            state.current_route = "document_fact"

        self._trace(
            state,
            node_name="execution_dispatch",
            model_used="n/a",
            tools_used=["route_dispatch"],
            relevant_output_ids=[
                state.current_route
            ] if state.current_route else [],
        )
        return state

    def _aggregate_results(self, state: WorkflowState) -> WorkflowState:
        state.retrieved_evidence = EvidenceNormalizer.normalize(
            state.retrieved_evidence
        )

        state.aggregated_results = {
            "document_results": state.document_results,
            "document_fact_results": state.document_fact_results,
            "data_results": state.data_results,
            "code_results": state.code_results,
            "vision_results": state.vision_results,
            "reasoning_results": state.reasoning_results,
            "retrieved_evidence": state.retrieved_evidence,
        }

        self._trace(
            state,
            node_name="aggregate_results",
            model_used="n/a",
            tools_used=["result_aggregation"],
            relevant_output_ids=["aggregated_results"],
        )

        return state

    def _complexity_gate(self, state: WorkflowState) -> WorkflowState:
        decision = ComplexityGate().evaluate(state.aggregated_results)

        state.synthesis_required = bool(
            decision.get("synthesis_required", False)
        )

        self._trace(
            state,
            node_name="complexity_gate",
            model_used="n/a",
            tools_used=["ComplexityGate"],
            relevant_output_ids=[
                "synthesis_required"
                if state.synthesis_required
                else "synthesis_not_required"
            ],
        )
        return state

    def _synthesis(self, state: WorkflowState) -> WorkflowState:
        self.telemetry.record_tool("SynthesisNode")

        if not state.synthesis_required:
            return state

        synthesis_node = SynthesisNode(
            telemetry=self.telemetry,
        )

        result = synthesis_node.run(
            state.user_query,
            state.retrieved_evidence,
            state.data_results,
            state.code_results,
            state.vision_results,
            state.conversation_history,
        )

        state.synthesis_result = result

        self._trace(
            state,
            node_name="synthesis",
            model_used=self._model_name(synthesis_node.model),
            tools_used=["SynthesisNode"],
            relevant_output_ids=["synthesis_result"],
        )
        return state

    def _final_answer(self, state: WorkflowState) -> WorkflowState:
        # Case 0: Deterministic document fact extraction
        field = DocumentFactExtractor.detect_field(state.user_query)

        if (
            field
            and state.retrieved_evidence
            and any(
                isinstance(item, dict) and item.get("content")
                for item in state.retrieved_evidence
            )
        ):
            result = DocumentFactExtractor.extract(
                query=state.user_query,
                evidence=evidence,
            )

            if result.success:
                state.document_fact_results.append(
                    {
                        "answer": result.answer,
                        "evidence_id": result.evidence_id,
                        "field": result.field,
                        "method": "deterministic_document_fact_extraction",
                    }
                )

                state.final_answer = result.answer

                self._trace(
                    state,
                    node_name="document_fact_extraction",
                    model_used="n/a",
                    tools_used=["DocumentFactExtractor"],
                    relevant_output_ids=[
                        result.evidence_id
                    ] if result.evidence_id else [],
                )

                return state

        # Case 1: A synthesis result exists
        if state.synthesis_result:
            answer = state.synthesis_result.get("answer")

            if answer:
                state.final_answer = answer

                self._trace(
                    state,
                    node_name="final_answer",
                    model_used="n/a",
                    tools_used=["answer_selection"],
                    relevant_output_ids=["final_answer"],
                )
                return state

        # Case 2: Use the reasoning result
        if state.reasoning_results:
            latest_reasoning = state.reasoning_results[-1]

            answer = latest_reasoning.get("answer")

            if answer:
                state.final_answer = answer

                self._trace(
                    state,
                    node_name="final_answer",
                    model_used="n/a",
                    tools_used=["answer_selection"],
                    relevant_output_ids=["final_answer"],
                )
                return state

        # Case 3: Fallback for deterministic analysis
        state.final_answer = (
            f"Analysis completed with "
            f"{len(state.retrieved_evidence)} evidence item(s), "
            f"{len(state.data_results)} data result(s), and "
            f"{len(state.vision_results)} vision result(s)."
        )

        self._trace(
            state,
            node_name="final_answer",
            model_used="n/a",
            tools_used=["answer_selection"],
            relevant_output_ids=["final_answer"],
        )
        return state

    def _verifier(self, state: WorkflowState) -> WorkflowState:
        answer = state.final_answer or state.synthesis_result.get(
            "answer",
            ""
        )

        verification_evidence = [
            *state.retrieved_evidence,
            *state.data_results,
            *state.code_results,
            *state.vision_results,
        ]

        synthesis_result = state.synthesis_result or {}
        aggregated_results = getattr(
            state,
            "aggregated_results",
            {},
        ) or {}

        analysis_answer = (
            state.final_answer
            or synthesis_result.get("answer")
            or ""
        )

        if not isinstance(analysis_answer, str):
            analysis_answer = str(analysis_answer)

        def extract_section(text: str, title: str) -> str:
            if not text:
                return ""

            pattern = re.compile(
                rf"(?ims)^\s*{re.escape(title)}\s*:\s*$"
                rf"(.*?)(?=^\s*[A-Za-z][A-Za-z &/_-]*\s*:\s*$|\Z)"
            )

            match = pattern.search(text)

            if not match:
                return ""

            return match.group(1).strip()

        def extract_bullets(text: str) -> list[str]:
            if not text:
                return []

            return [
                line.lstrip("-* ").strip()
                for line in text.splitlines()
                if line.strip().startswith(("-", "*"))
                and line.lstrip("-* ").strip()
            ]

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", analysis_answer)
            if paragraph.strip()
        ]

        executive_summary = (
            synthesis_result.get("executive_summary")
            or extract_section(
                analysis_answer,
                "Executive Summary",
            )
            or (paragraphs[0] if paragraphs else analysis_answer)
        )

        key_findings = (
            synthesis_result.get("key_findings")
            or synthesis_result.get("findings")
            or aggregated_results.get("findings")
            or extract_section(
                analysis_answer,
                "Key Findings",
            )
            or extract_bullets(analysis_answer)
        )

        detailed_analysis = (
            synthesis_result.get("detailed_analysis")
            or extract_section(
                analysis_answer,
                "Detailed Analysis",
            )
            or analysis_answer
        )

        conclusion = (
            synthesis_result.get("conclusion")
            or extract_section(
                analysis_answer,
                "Conclusion",
            )
            or (paragraphs[-1] if paragraphs else analysis_answer)
        )

        supporting_evidence = []

        for item in state.retrieved_evidence:
            if not isinstance(item, dict):
                continue

            supporting_evidence.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    "source_filename": item.get("source_filename"),
                    "page_number": item.get("page_number"),
                    "chunk_id": item.get("chunk_id"),
                    "citation_id": item.get("citation_id"),
                    "content": item.get(
                        "content",
                        item.get("text", ""),
                    ),
                }
            )

        report = {
            "title": "SOVARA ANALYSIS REPORT",
            "sections": {
                "answer": answer,
                "evidence_count": len(verification_evidence),
                "document_results": state.document_results,
                "data_results": state.data_results,
                "vision_results": state.vision_results,

                "executive_summary": executive_summary,
                "key_findings": key_findings,
                "detailed_analysis": detailed_analysis,
                "supporting_evidence": supporting_evidence,
                "verification": {
                    "status": state.verification_status,
                    "results": state.verification_results,
                },
                "conclusion": conclusion,
            },
            "appendix": {
                "evidence_registry": {
                    "retrieved_evidence": state.retrieved_evidence,
                    "document_results": state.document_results,
                    "data_results": state.data_results,
                    "vision_results": state.vision_results,
                    "code_results": getattr(
                        state,
                        "code_results",
                        [],
                    ),
                },
                "execution_telemetry": (
                    state.execution_telemetry or {}
                ),
                "generated_artifacts": list(
                    state.generated_deliverables or []
                ),
            },
        }

        verifier = Verifier()

        verification = verifier.verify(
            answer,
            verification_evidence,
            report,
        )

        verification_status = verification.get(
            "verification_status",
            "passed",
        )

        state.verification_results = [verification]
        state.verification_status = verification_status

        state.execution_telemetry = self.telemetry.summary()

        self._trace(
            state,
            node_name="verifier",
            model_used="n/a",
            tools_used=["Verifier"],
            relevant_output_ids=[
                "verification_1",
                verification_status,
                *verification.get("failures", []),
            ],
        )

        return state

    def _verification_route(self, state: WorkflowState) -> str:
        if state.verification_status == "passed":
            return "pass"

        if (
            state.verification_status == "failed"
            and state.repair_attempts < self.max_repair_attempts
        ):
            return "fail_retry"

        return "fail_terminal"

    def _repair(self, state: WorkflowState) -> WorkflowState:
        if state.verification_status == "passed":
            return state

        state.repair_attempts += 1

        if state.repair_attempts >= self.max_repair_attempts:
            state.verification_status = "failed_terminal"
            return state

        verification_failures = []

        if state.verification_results:
            verification = state.verification_results[0]
            verification_failures = list(
                verification.get("failures", [])
            )

            numeric_validation = verification.get(
                "numeric_validation",
                [],
            )

            if numeric_validation:
                verification_failures.append(
                    f"numeric_validation_details: {numeric_validation}"
                )

        verification_evidence = [
            *state.retrieved_evidence,
            *state.data_results,
            *state.code_results,
            *state.vision_results,
        ]

        repair_node = RepairNode(
            max_attempts=self.max_repair_attempts,
            telemetry=self.telemetry,
        )

        repaired = repair_node.repair(
            {
                "final_answer": state.final_answer,
                "synthesis_result": state.synthesis_result,
            },
            verification_failures,
            verification_evidence,
        )

        state.final_answer = repaired.get(
            "final_answer",
            state.final_answer,
        )

        state.synthesis_result = repaired.get(
            "synthesis_result",
            state.synthesis_result,
        )

        self._trace(
            state,
            node_name="repair",
            model_used=self._model_name(getattr(repair_node, "model", None)),
            tools_used=["RepairNode"],
            relevant_output_ids=[
                "repaired_answer"
            ],
        )

        return state

    def _deliverable(self, state: WorkflowState) -> WorkflowState:

        state.execution_telemetry = self.telemetry.summary()

        synthesis_result = (
            state.synthesis_result
            if isinstance(state.synthesis_result, dict)
            else {}
        )

        aggregated_results = getattr(
            state,
            "aggregated_results",
            {},
        ) or {}

        analysis_answer = (
            state.final_answer
            or synthesis_result.get("answer")
            or ""
        )

        if not isinstance(analysis_answer, str):
            analysis_answer = str(analysis_answer)

        def extract_section(text: str, title: str) -> str:
            if not text:
                return ""

            pattern = re.compile(
                rf"(?ims)^\s*{re.escape(title)}\s*:?\s*$"
                rf"(.*?)(?=^\s*[A-Za-z][A-Za-z &/_-]*\s*:?\s*$|\Z)"
            )

            match = pattern.search(text)

            if not match:
                return ""

            return match.group(1).strip()

        def paragraphs(text: str) -> list[str]:
            return [
                part.strip()
                for part in re.split(
                    r"\r?\n\s*\r?\n",
                    text,
                )
                if part.strip()
            ]

        executive_summary = (
            synthesis_result.get("executive_summary")
            or extract_section(
                analysis_answer,
                "Executive Summary",
            )
        )

        if not executive_summary:
            answer_paragraphs = paragraphs(
                analysis_answer
            )

            executive_summary = (
                answer_paragraphs[0]
                if answer_paragraphs
                else analysis_answer
            )

        key_findings = (
            synthesis_result.get("key_findings")
            or synthesis_result.get("findings")
            or aggregated_results.get("key_findings")
            or aggregated_results.get("findings")
        )

        if not key_findings:
            findings_text = extract_section(
                analysis_answer,
                "Key Findings",
            )

            if findings_text:
                key_findings = [
                    (
                        line.strip()[2:].strip()
                        if line.strip().startswith(("- ", "* "))
                        else line.strip()
                    )
                    for line in findings_text.splitlines()
                    if line.strip()
                ]

        if key_findings is None:
            key_findings = []
        elif isinstance(key_findings, str):
            key_findings = [
                line.strip()
                for line in key_findings.splitlines()
                if line.strip()
            ]
        elif not isinstance(key_findings, list):
            key_findings = [key_findings]

        detailed_analysis = (
            synthesis_result.get("detailed_analysis")
            or extract_section(
                analysis_answer,
                "Detailed Analysis",
            )
            or analysis_answer
        )

        conclusion = (
            synthesis_result.get("conclusion")
            or extract_section(
                analysis_answer,
                "Conclusion",
            )
        )

        if not conclusion:
            answer_paragraphs = paragraphs(
                analysis_answer
            )

            conclusion = (
                answer_paragraphs[-1]
                if answer_paragraphs
                else analysis_answer
            )

        supporting_evidence = []

        for item in state.retrieved_evidence:
            if not isinstance(item, dict):
                continue

            supporting_evidence.append(
                {
                    "evidence_id": item.get(
                        "evidence_id"
                    ),
                    "source_filename": item.get(
                        "source_filename"
                    ),
                    "page_number": item.get(
                        "page_number"
                    ),
                    "chunk_id": item.get(
                        "chunk_id"
                    ),
                    "citation_id": item.get(
                        "citation_id"
                    ),
                    "reference": item.get(
                        "reference"
                    ),
                    "content": item.get(
                        "content",
                        item.get(
                            "text",
                            item.get(
                                "reference",
                                "",
                            ),
                        ),
                    ),
                }
            )

        runtime_telemetry = {}

        if (
            hasattr(self, "telemetry")
            and self.telemetry
        ):
            runtime_telemetry = (
                self.telemetry.summary()
                or {}
            )

        state_telemetry = (
            state.execution_telemetry
            or {}
        )

        execution_telemetry = {
            **runtime_telemetry,
            **state_telemetry,
        }

        report = {
            "title": "SOVARA ANALYSIS REPORT",
            "sections": {
                "executive_summary":
                    executive_summary,
                "key_findings":
                    key_findings,
                "detailed_analysis":
                    detailed_analysis,
                "supporting_evidence":
                    supporting_evidence,
                "verification": {
                    "status":
                        state.verification_status,
                    "results":
                        state.verification_results,
                },
                "conclusion":
                    conclusion,
            },
            "appendix": {
                "evidence_registry": {
                    "retrieved_evidence":
                        state.retrieved_evidence,
                    "document_results":
                        state.document_results,
                    "data_results":
                        state.data_results,
                    "vision_results":
                        state.vision_results,
                    "code_results": getattr(
                        state,
                        "code_results",
                        [],
                    ),
                },
                "execution_telemetry":
                    execution_telemetry,
                "generated_artifacts":
                    list(
                        state.generated_deliverables
                        or []
                    ),
            },
        }

        requested_format = (
            state.requested_deliverable or ""
        ).lower().strip()

        # ---------------------------------------------------------
        # DOCX REPORT
        # ---------------------------------------------------------
        if requested_format in {"report", "docx"}:
            output_path = (
                f"outputs/{state.request_id}_report.docx"
            )

            generated_path = DeliverableNode().generate(
                report,
                output_path,
            )

            tool_used = "python-docx"

        # ---------------------------------------------------------
        # JSON REPORT
        # ---------------------------------------------------------
        elif requested_format == "json":
            import json

            output_path = (
                f"outputs/{state.request_id}_report.json"
            )

            with open(
                output_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    report,
                    file,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            generated_path = output_path
            tool_used = "json"

        # ---------------------------------------------------------
        # NO DELIVERABLE REQUESTED
        # ---------------------------------------------------------

        elif not requested_format:
            state.generated_deliverables = []

            self._trace(
                state,
                node_name="deliverable",
                model_used="n/a",
                tools_used=[],
                relevant_output_ids=[],
            )

            return state

        # ---------------------------------------------------------
        # UNSUPPORTED FORMAT
        # ---------------------------------------------------------
        else:
            state.generated_deliverables = []

            self._trace(
                state,
                node_name="deliverable",
                model_used="n/a",
                tools_used=[],
                relevant_output_ids=[],
            )

            return state

        state.generated_deliverables = [generated_path]

        self._trace(
            state,
            node_name="deliverable",
            model_used="n/a",
            tools_used=[tool_used],
            relevant_output_ids=[
                generated_path
            ],
        )

        return state


    def build(self):
        self.graph.add_node("input_processor", self._input_processor)
        self.graph.add_node("task_analyzer", self._task_analyzer)
        self.graph.add_node("policy_router", self._policy_router)
        self.graph.add_node("execution_dispatch", self._execution_dispatch)
        self.graph.add_node("document_route", self._document_route)
        self.graph.add_node("document_fact", self._document_fact_route)
        self.graph.add_node("vault_route", self._vault_route)
        self.graph.add_node("data_route", self._data_route)
        self.graph.add_node("vision_route", self._vision_route)
        self.graph.add_node("reasoning_route", self._reasoning_route)
        self.graph.add_node("code_execution", self._code_execution)
        self.graph.add_node("aggregate_results", self._aggregate_results)
        self.graph.add_node("complexity_gate", self._complexity_gate)
        self.graph.add_node("synthesis", self._synthesis)
        self.graph.add_node("final_answer", self._final_answer)
        self.graph.add_node("verifier", self._verifier)
        self.graph.add_node("repair", self._repair)
        self.graph.add_node("deliverable", self._deliverable)

        self.graph.set_entry_point("input_processor")
        self.graph.add_edge("input_processor", "task_analyzer")
        self.graph.add_edge("task_analyzer", "policy_router")
        self.graph.add_conditional_edges(
            "policy_router",
            lambda state: "dispatch" if state.selected_routes else "aggregate_results",
            {"dispatch": "execution_dispatch", "aggregate_results": "aggregate_results"},
        )
        self.graph.add_conditional_edges(
            "execution_dispatch",
            lambda state: state.current_route if state.current_route else "aggregate_results",
            {
                "document": "document_route",
                "vault": "vault_route",
                "data": "data_route",
                "vision": "vision_route",
                "reasoning": "reasoning_route",
                "document_fact": "document_fact",
                "code_execution": "code_execution",
                "aggregate_results": "aggregate_results",
            },
        )
        self.graph.add_conditional_edges(
            "document_route",
            self._should_use_document_fact_extraction,
            {
                "document_fact": "document_fact",
                "reasoning": "execution_dispatch",
            },
        )
        self.graph.add_edge(
            "document_fact",
            "aggregate_results",
        )
        self.graph.add_edge("data_route", "execution_dispatch")
        self.graph.add_edge("vision_route", "execution_dispatch")
        self.graph.add_edge("reasoning_route", "execution_dispatch")
        self.graph.add_edge("code_execution", "execution_dispatch")
        self.graph.add_edge("vault_route", "execution_dispatch")
        self.graph.add_edge("aggregate_results", "complexity_gate")
        self.graph.add_conditional_edges(
            "complexity_gate",
            lambda state: "synthesis" if state.synthesis_required else "final_answer",
            {
                "synthesis": "synthesis",
                "final_answer": "final_answer",
            },
        )

        self.graph.add_edge("synthesis", "final_answer")

        self.graph.add_edge("final_answer", "verifier")
        self.graph.add_conditional_edges(
            "verifier",
            self._verification_route,
            {
                "pass": "deliverable",
                "fail_retry": "repair",
                "fail_terminal": END,
            },
        )
        self.graph.add_edge("repair", "verifier")
        self.graph.add_edge("deliverable", END)
        return self.graph.compile()
