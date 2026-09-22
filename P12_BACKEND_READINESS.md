# P12 Backend Readiness Audit

## Scope

P12 is a backend-readiness and frontend-integration pass over the existing SOVARA V2 backend.

P1-P11 and Intelligence Hardening remain authoritative and must not be rewritten or replaced.

Existing authorities:

- P5 â€” execution and sandbox security
- P6 â€” durable task state and checkpointing
- P7 â€” governance, policy and audit
- P8 â€” verification and evaluation
- P9 â€” human approval
- P11 â€” inference, performance and response controls
- Intelligence Hardening â€” RAG V2.5, Budget Governor, Run Trace and Untrusted Content Boundary

---

## Capability Matrix

| Requirement | Existing Capability | Location | Status | Required Work | Owner |
|---|---|---|---|---|---|
| Canonical Task | Durable task identity and lifecycle | `app/state/models.py`, `app/state/manager.py` | READY | Reuse P6 task identity | P6 |
| Canonical Run | No independent durable run identity; `task_id` is existing execution identity; SSE `run_id` is an alias of `task_id` | `app/state/`, `app/planner/`, `app/api/routes.py` | PARTIAL | Add run/status retrieval and recovery contract without competing persistence | P12 |
| Conversation | Durable conversation/message persistence | `app/services/conversation_service.py` | READY | Associate with execution contract where required | Existing |
| Workflow State | Rich workflow state exists | `app/state/workflow_state.py` | PARTIAL | Add only required frontend contract fields | P12 |
| Durable State | SQLite P6 state store with optimistic versioning | `app/state/store.py` | READY | Reuse | P6 |
| Task Status | PENDING/RUNNING/COMPLETED/FAILED/CANCELLED | `app/state/models.py` | READY | Map to frontend lifecycle | P12 |
| Semantic Lifecycle | Internal task and plan states exist | `app/state/models.py`, `app/planner/models.py` | PARTIAL | Add deterministic frontend mapping | P12 |
| Semantic Stages | Frontend-safe semantic stage projection exists | `app/state/semantic_stage.py`, `app/state/semantic_stage_projection.py`, `app/state/workflow_stage_mapping.py`, `app/state/execution_trace_projection.py` | READY | Reuse projection for frontend lifecycle/stage display | P12 |
| Execution Events | User-safe execution event projection exists over Run Trace events | `app/state/execution_event_projection.py`, `app/services/run_trace.py` | READY | Reuse projection; do not expose internal execution details | P12 |
| Run Trace | Ordered in-memory execution trace | `app/services/run_trace.py` | READY | Reuse; P6 remains durable authority | Existing |
| Streaming | Existing SSE `/analyze/stream` with canonical `task_id`/`run_id`, event IDs, sequence numbers and safe failure messages | `app/api/routes.py` | PARTIAL | Add truthful semantic stage projection and lifecycle coverage without creating a second stream | P12 |
| Streaming Replay | Durable completed/failed result replay and existing-task reconnect protection use the canonical task state | `app/api/routes.py`, `app/state/manager.py`, `app/state/store.py` | READY | Reuse existing SSE contract; do not create a second stream | P12 |
| Cancellation | Durable P6 cancellation exists; executor stops new scheduling and observes cancellation | `app/state/manager.py`, `app/planner/executor.py` | PARTIAL | Define/verify behavior for already-running work, races and terminal-state cancellation | P12 |
| Planner Cancellation | Cooperative cancellation checks stop new scheduling and preserve durable CANCELLED state | `app/planner/executor.py` | PARTIAL | Active broker/verifier calls remain non-interruptible; verify race and parallel semantics | P12 |
| P7 Governance | Permission/risk enforcement | `app/governance/policy.py` | READY | Reuse | P7 |
| P5 Execution Security | Permission/sandbox enforcement | `app/execution/policy.py` | READY | Reuse | P5 |
| P8 Verification | Execution verification integrated | `app/planner/executor.py` | READY | Reuse | P8 |
| P9 Approval Core | Durable approval manager/store/gate | `app/hitl/` | READY | Reuse | P9 |
| Approval API | No frontend approval API found | `app/api/routes.py` | MISSING | Add thin P9-backed endpoints | P12 |
| Telemetry | Request-scoped execution telemetry | `app/services/execution_telemetry.py` | PARTIAL | Add frontend-safe projection | P12 |
| Context | Context manager and workflow context | `app/services/context_manager.py`, `app/state/workflow_state.py` | READY | Reuse | Existing |
| Sources/RAG | Knowledge Vault, retrieval, RAG V2.5, evidence normalization | `app/rag/`, `app/services/` | READY | Expose frontend-safe contract | P12 |
| Source/Run Association | Evidence exists in workflow state | `app/state/workflow_state.py` | PARTIAL | Associate with canonical execution contract | P12 |
| Untrusted Content | External/retrieved content classification | `app/services/untrusted_content.py` | READY | Preserve | Hardening |
| History | Durable conversation storage | `app/services/conversation_service.py` | PARTIAL | Add task/run history retrieval | P12 |
| History Pagination | No task/history listing API found | `app/services/`, `app/api/` | MISSING | Minimal paginated query layer | P12 |
| Result Preferences | No semantic frontend preference contract found | Workflow/API | MISSING | Add BRIEF/DETAILED/TABLE/COMPARISON | P12 |
| Error Contract | FastAPI HTTPException exists | `app/api/routes.py` | PARTIAL | Add stable frontend error model | P12 |
| Raw Error Protection | SSE no longer exposes raw `str(exc)`; server logs retain diagnostics | `app/api/routes.py` | PARTIAL | Complete stable structured error contract for API/stream failures | P12 |
| API Authorization | No route-level principal/current-user authorization found | `app/api/routes.py` | MISSING | Establish server-side resource authorization | Establish server-side resource authorization | P12 |
| Tool Permissions | Tool permissions are declared and validated | `app/tools/registry.py`, `app/planner/tool_selector.py` | READY | Reuse; not a substitute for API authorization | Existing |
| Analysis Persistence | `analysis_store` is process-local | `app/api/routes.py` | PARTIAL | Do not rely on it for durable recovery | Do not rely on it for durable recovery | P12 |
| Database Schema | P6, Conversation and P9 stores already exist | `app/state/`, `app/services/`, `app/hitl/` | READY | Reuse existing stores | Existing |
| Database Migration | No proven missing persistent capability yet | Existing SQLite stores | BLOCKED | Only migrate if implementation proves necessary | P12 |
| Budget Governor | Lock-protected execution budgets | `app/governance/budget.py` | READY | Preserve | Hardening |
| RAG V2.5 | Hybrid retrieval, fusion, compression, diversity, citations | `app/rag/` | READY | Preserve | Hardening |
| Untrusted Boundary | Trust classification and annotation | `app/services/untrusted_content.py` | READY | Preserve | Hardening |

---

## Canonical Identity

Current evidence establishes:

- `task_id` is the existing durable execution identity.
- P6 persists task state using `task_id`.
- Planner/executor uses `task_id`.
- P7 and P9 associate execution/governance/approval with `task_id`.
- `trace_id` is observational Run Trace identity.
- `request_id` is an API/workflow request identifier.
- No independent durable `run_id` implementation was found.

### P12 Decision

Do not create a second durable execution entity merely to satisfy frontend terminology.

The frontend run contract should be backed by the canonical P6 `task_id`. If an API-level `run_id` is exposed, it must remain an alias/projection of the canonical execution identity rather than creating competing persistence.

P6 remains authoritative for execution state.

---

## Frontend Lifecycle

Required semantic lifecycle:

- QUEUED
- PLANNING
- EXECUTING
- WAITING_FOR_APPROVAL
- VERIFYING
- COMPLETED
- FAILED
- CANCELLED

Existing P6/P11/planner states must be mapped into this representation rather than replaced.

Terminal-state rules:

- COMPLETED cannot become CANCELLED.
- FAILED and CANCELLED are terminal unless an existing recovery mechanism creates a new execution version.
- WAITING_FOR_APPROVAL must correspond to an actual P9 approval request.

---

## Semantic Stages

Frontend-safe stages:

- UNDERSTANDING
- PLANNING
- RETRIEVING
- ANALYZING
- GENERATING
- VERIFYING
- WAITING_FOR_APPROVAL
- COMPLETED
- FAILED
- CANCELLED

Stage contract:

```text
stage_id
run_id
stage_type
status
display_label
sequence
started_at
completed_at
