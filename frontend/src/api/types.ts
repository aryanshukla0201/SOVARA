export interface LlmEvent {
  type?: string;
  model_name?: string;
  duration_ms?: number | null;
  success?: boolean;
  input_chars?: number | null;
  output_chars?: number | null;
  [key: string]: unknown;
}

export interface ExecutionEvent {
  type?: string;
  tool?: string;
  success?: boolean;
  return_code?: number;
  duration_ms?: number | null;
  timeout?: boolean;
  [key: string]: unknown;
}

export interface ExecutionTelemetry {
  local_inference: boolean;
  processing_location: string;
  models_used: string[];
  llm_calls: number;
  llm_total_duration_ms: number;
  llm_average_duration_ms: number;
  llm_events: LlmEvent[];
  external_api_calls: number;
  network_calls: number;
  cloud_uploads: number;
  files_processed: number;
  tools_used: string[];
  sandbox_executions: number;
  sandbox_successes: number;
  sandbox_failures: number;
  sandbox_timeouts: number;
  execution_events: ExecutionEvent[];
  no_external_calls: boolean;
}

export interface SemanticStageView {
  stage_id: string;
  run_id: string;
  stage_type: string;
  status: string;
  display_label: string;
  sequence: number;
  started_at?: string | null;
  completed_at?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface EvidenceItem {
  [key: string]: unknown;
}

export interface VerificationResult {
  [key: string]: unknown;
}

export interface AnalysisResponse {
  request_id: string;
  task_id?: string;
  conversation_id?: string | null;
  status: string;
  final_answer: string;
  evidence: EvidenceItem[];
  verification_status?: string | null;
  verification_results: VerificationResult[];
  stages: SemanticStageView[];
  execution_events: ExecutionEvent[];
  traceability?: unknown;
  execution_telemetry?: ExecutionTelemetry;
  generated_deliverables: string[];
}

export interface AnalysisStreamEvent {
  type: 'workflow' | 'completed' | 'error' | string;
  [key: string]: unknown;
}

export interface VaultDocumentResponse {
  documents?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface VaultSearchResult {
  evidence_id?: string;
  source_file_id?: string;
  source_filename?: string;
  page_number?: number | null;
  chunk_id?: string | null;
  [key: string]: unknown;
}

export interface VaultSearchResponse {
  results: VaultSearchResult[];
  [key: string]: unknown;
}

export interface TaskResponse {
  [key: string]: unknown;
}

export interface ApprovalResponse {
  approval_id: string;
  task_id: string;
  step_id: string;
  tool_name: string;
  reason: string;
  risk_level: string;
  requested_action: string;
  requested_arguments_summary: string;
  created_at: string;
  expires_at: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';
  metadata: Record<string, unknown>;
}

export interface ReportResponse {
  [key: string]: unknown;
}
