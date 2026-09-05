from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.state.workflow_state import WorkflowState
from app.tools.documents.pdf_parser import PDFParser
from app.tools.documents.retriever import DocumentRetriever
from app.tools.vision.image_analyzer import VisionAnalyzer
from app.workflow.nodes.complexity_gate import ComplexityGate
from app.workflow.nodes.data_node import DataNode
from app.workflow.nodes.deliverable import DeliverableNode
from app.workflow.nodes.document_node import DocumentNode
from app.workflow.nodes.input_processor import detect_input_modalities
from app.workflow.nodes.policy_router import PolicyRouter
from app.workflow.nodes.reasoning_node import ReasoningNode
from app.workflow.nodes.repair import RepairNode
from app.workflow.nodes.synthesis import SynthesisNode
from app.workflow.nodes.task_analyzer import TaskAnalyzer
from app.workflow.nodes.vision_node import VisionNode
from app.workflow.nodes.verifier import Verifier
from app.services.execution_telemetry import ExecutionTelemetry


class WorkflowGraph:
    def __init__(self):
        self.graph = StateGraph(WorkflowState)
        self.max_repair_attempts = 3

        # Request execution telemetry
        self.telemetry = ExecutionTelemetry()

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
        state.task_state = TaskAnalyzer(telemetry=self.telemetry).analyze(state.user_query, input_types)

        self._trace(
            state,
            node_name="task_analyzer",
            model_used="qwen3",
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
            "reasoning": 4,
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

    def _document_route(self, state: WorkflowState) -> WorkflowState:
        document_node = DocumentNode(retriever=DocumentRetriever())
        for file_record in state.uploaded_files:
            if file_record.file_type != "pdf":
                continue
            evidence = document_node.run(file_record.storage_path, state.user_query, file_record.file_id)
            state.retrieved_evidence.extend([item.model_dump() for item in evidence])
            state.document_results.append({
                "source_file": file_record.original_name,
                "file_id": file_record.file_id,
                "pages": len(PDFParser.extract_text(file_record.storage_path).get("pages", [])),
                "evidence_count": len(evidence),
            })

            self._trace(
            state,
            node_name="document_route",
            model_used="n/a",
            tools_used=["PyMuPDF", "DocumentRetriever"],
            relevant_output_ids=[
                item["file_id"]
                for item in state.document_results
            ],
        )
        return state

    def _data_route(self, state: WorkflowState) -> WorkflowState:
        data_node = DataNode()

        for file_record in state.uploaded_files:

            if file_record.file_type not in {"csv", "xlsx"}:
                continue

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

            result = VisionNode(
                telemetry=self.telemetry
            ).run(
                file_record.storage_path,
                state.user_query
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
                model_used="gemma3:4b-it-qat",
                tools_used=["VisionAnalyzer"],
                relevant_output_ids=[
                    f"{file_record.file_id}_ev_{index:03d}"
                    for index in range(1, len(observations) + 1)
                ],
            )

        return state

    def _reasoning_route(self, state: WorkflowState) -> WorkflowState:
        result = ReasoningNode(telemetry=self.telemetry).run(
            user_query=state.user_query,
            evidence=state.retrieved_evidence,
            data_results=state.data_results,
            vision_results=state.vision_results,
        )

        state.reasoning_results.append(result)

        self._trace(
            state,
            node_name="reasoning_route",
            model_used="qwen3",
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
        state.completed_routes = list(dict.fromkeys(state.completed_routes + [state.current_route]))

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
        state.aggregated_results = {
            "document_results": state.document_results,
            "data_results": state.data_results,
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
        if not state.synthesis_required:
            return state

        result = SynthesisNode(telemetry=self.telemetry).run(
            state.user_query,
            state.retrieved_evidence,
            state.data_results,
            state.vision_results,
        )

        state.synthesis_result = result

        self._trace(
            state,
            node_name="synthesis",
            model_used="qwen3",
            tools_used=["SynthesisNode"],
            relevant_output_ids=["synthesis_result"],
        )
        return state

    def _final_answer(self, state: WorkflowState) -> WorkflowState:

        # Case 1: A synthesis result exists
        if state.synthesis_result:
            answer = state.synthesis_result.get("answer")

            if answer:
                state.final_answer = answer

                self._trace(
                    state,
                    node_name="final_answer",
                    model_used="qwen3",
                    tools_used=["answer_selection"],
                    relevant_output_ids=["final_answer"],
                )
                print("[GRAPH DEBUG] final_answer -> verifier")
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
                    model_used="qwen3",
                    tools_used=["answer_selection"],
                    relevant_output_ids=["final_answer"],
                )
                print("[GRAPH DEBUG] final_answer -> verifier")
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
        print("[GRAPH DEBUG] final_answer -> verifier")
        return state

    def _verifier(self, state: WorkflowState) -> WorkflowState:
        answer = state.final_answer or state.synthesis_result.get(
            "answer",
            ""
        )

        verification_evidence = [
            *state.retrieved_evidence,
            *state.data_results,
            *state.vision_results,
        ]

        report = {
            "title": "Analysis Report",
            "sections": {
                "answer": answer,
                "evidence_count": len(verification_evidence),
                "document_results": state.document_results,
                "data_results": state.data_results,
                "vision_results": state.vision_results,
            },
        }

        verification = Verifier().verify(
            answer,
            verification_evidence,
            report,
        )

        verification_status = verification.get(
            "verification_status",
            "passed",
        )

        print("\n===== VERIFIER RESULT =====")
        print(verification)
        print("===========================\n")

        state.verification_results = [verification]
        state.verification_status = verification_status

        state.execution_telemetry = self.telemetry.summary()


        self._trace(
            state,
            node_name="verifier",
            model_used="qwen3",
            tools_used=["Verifier"],
            relevant_output_ids=[
                "verification_1",
                verification_status,
                *verification.get("failures", []),
            ],
        )

        print(
            f"[VERIFIER STATE] "
            f"verification_status={state.verification_status}"
        )

        return state

    def _verification_route(self, state: WorkflowState) -> str:
        if state.verification_status == "passed":
            print(
                f"[VERIFICATION ROUTER] status=passed "
                f"attempts={state.repair_attempts} -> deliverable"
            )
            return "pass"

        if (
            state.verification_status == "failed"
            and state.repair_attempts < self.max_repair_attempts
        ):
            print(
                f"[VERIFICATION ROUTER] status=failed "
                f"attempts={state.repair_attempts} -> repair"
            )
            return "fail_retry"

        print(
            f"[VERIFICATION ROUTER] status={state.verification_status} "
            f"attempts={state.repair_attempts} -> END"
        )
        return "fail_terminal"

    def _repair(self, state: WorkflowState) -> WorkflowState:
        if state.verification_status == "passed":
            return state

        state.repair_attempts += 1

        if state.repair_attempts >= self.max_repair_attempts:
            state.verification_status = "failed_terminal"
            return state

        verification_failures = (
            state.verification_results[0].get("failures", [])
            if state.verification_results
            else []
        )

        verification_evidence = []

        verification_evidence.extend(
            state.retrieved_evidence
        )

        verification_evidence.extend(
            state.data_results
        )

        verification_evidence.extend(
            state.vision_results
        )

        repaired = RepairNode(
            max_attempts=self.max_repair_attempts,
            telemetry=self.telemetry
        ).repair(
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
            model_used="qwen3",
            tools_used=["RepairNode"],
            relevant_output_ids=[
                "repaired_answer"
            ],
        )

        return state

    def _deliverable(self, state: WorkflowState) -> WorkflowState:

        state.execution_telemetry = self.telemetry.summary()

        report = {
            "title": "Analysis Report",
            "sections": {
                "answer": state.final_answer or state.synthesis_result.get(
                    "answer",
                    ""
                ),
                "evidence": [
                    *state.retrieved_evidence,
                    *state.data_results,
                    *state.vision_results,
                ],
                "documents": state.document_results,
                "data": state.data_results,
                "vision": state.vision_results,
                "verification": state.verification_results,
                "verification_status": state.verification_status,
            },
        }

        requested_format = (
            state.requested_deliverable or "report"
        ).lower().strip()

        # ---------------------------------------------------------
        # DOCX REPORT
        # ---------------------------------------------------------
        if requested_format == "report":
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
        # SAFE FALLBACK
        # ---------------------------------------------------------
        else:
            output_path = (
                f"outputs/{state.request_id}_report.docx"
            )

            generated_path = DeliverableNode().generate(
                report,
                output_path,
            )

            tool_used = "python-docx"

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
        self.graph.add_node("data_route", self._data_route)
        self.graph.add_node("vision_route", self._vision_route)
        self.graph.add_node("reasoning_route", self._reasoning_route)
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
                "data": "data_route",
                "vision": "vision_route",
                "reasoning": "reasoning_route",
                "aggregate_results": "aggregate_results",
            },
        )
        self.graph.add_edge("document_route", "execution_dispatch")
        self.graph.add_edge("data_route", "execution_dispatch")
        self.graph.add_edge("vision_route", "execution_dispatch")
        self.graph.add_edge("reasoning_route", "execution_dispatch")
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
