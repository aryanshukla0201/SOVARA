from __future__ import annotations

from app.state.workflow_state import WorkflowState


class PolicyRouter:
    def route(self, state: WorkflowState) -> list[str]:
        routes: list[str] = []
        task = state.task_state

        if task is None:
            routes = ["vault", "reasoning"]
            state.selected_routes = list(dict.fromkeys(routes))
            return state.selected_routes

        capabilities = set(task.required_capabilities)

        file_types = {
            file.file_type
            for file in state.uploaded_files
        }

        has_document_files = bool(
            file_types & {"pdf", "docx"}
        )
        has_data_files = bool(
            file_types & {"csv", "xlsx", "xls"}
        )
        has_image_files = "image" in file_types

        if task.requires_rag or "document_analysis" in capabilities:
            if has_document_files:
                routes.append("document")
            elif not state.uploaded_files:
                routes.append("vault")

        if "data_analysis" in capabilities and has_data_files:
            routes.append("data")

        if task.requires_code:
            routes.append("code_execution")

        if (
            task.requires_vision
            or "vision_analysis" in capabilities
        ) and has_image_files:
            routes.append("vision")

        if "reasoning" in capabilities:
            routes.append("reasoning")
        elif not routes:
            routes.append("reasoning")

        deduped = list(dict.fromkeys(routes))
        state.selected_routes = deduped
        return state.selected_routes
