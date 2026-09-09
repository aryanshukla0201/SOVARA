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

        if task.requires_rag or "document_analysis" in capabilities:
            if state.uploaded_files:
                routes.append("document")
            else:
                routes.append("vault")

        if "data_analysis" in capabilities or task.requires_code:
            routes.append("data")

        if task.requires_vision or "vision_analysis" in capabilities:
            routes.append("vision")

        if "reasoning" in capabilities:
            routes.append("reasoning")
        elif not routes:
            routes.append("reasoning")

        deduped = list(dict.fromkeys(routes))
        state.selected_routes = deduped
        return state.selected_routes