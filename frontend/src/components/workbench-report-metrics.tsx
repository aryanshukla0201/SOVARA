type ReportTool = {
  detail: string;
};

const EXTERNAL_CALL_PATTERN = /external fetch|network|public socket|egress\s+(?:request|call)/i;
const NO_EXTERNAL_CALL_PATTERN = /no\s+external\s+fetch|no\s+network|egress\s+(?:syscalls|requests|calls):\s*0/i;

function Metric({ label, value, description }: {
  label: string;
  value: number;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-xs uppercase tracking-widest text-faint">{label}</p>
      </div>
      <p className="mt-2 font-display text-3xl font-medium tabular-nums leading-none">{value}</p>
      <p className="mt-2 text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

export function WorkbenchReportMetrics({
  tools,
  executionReport,
}: {
  tools: ReportTool[];
  executionReport?: {
    telemetry: Record<string, unknown>;
    traceability: unknown[];
    evidence: unknown[];
    verificationStatus: string;
    verificationResults: unknown[];
  };
}) {
  const externalCalls = tools.filter(
    (tool) =>
      EXTERNAL_CALL_PATTERN.test(tool.detail) &&
      !NO_EXTERNAL_CALL_PATTERN.test(tool.detail),
  ).length;

  const workflowSteps = executionReport?.traceability.length ?? 0;
  const telemetry = executionReport?.telemetry ?? {};

  const localInference = telemetry.local_inference === true;
  const processingLocation =
    typeof telemetry.processing_location === "string"
      ? telemetry.processing_location
      : "unknown";

  const llmCalls =
    typeof telemetry.llm_calls === "number"
      ? telemetry.llm_calls
      : 0;

  const modelsUsed = Array.isArray(telemetry.models_used)
    ? telemetry.models_used.join(", ")
    : "unknown";
  const evidenceCount = executionReport?.evidence.length ?? 0;
  const traceCount = executionReport?.traceability.length ?? 0;
  const verificationStatus =
    executionReport?.verificationStatus ?? "not run";

  return (
    <section aria-labelledby="workbench-report-calls">
      <p
        id="workbench-report-calls"
        className="font-mono text-xs uppercase tracking-widest text-faint"
      >
        Execution report
      </p>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <Metric
          label="Evidence"
          value={evidenceCount}
          description="Retrieved evidence records"
        />

        <Metric
          label="Trace events"
          value={traceCount}
          description="Execution trace events"
        />

        <Metric
          label="External calls"
          value={externalCalls}
          description="Outside the local fence"
        />

        <Metric
          label="Workflow steps"
          value={workflowSteps}
          description="Local execution steps"
        />

        <Metric
          label="LLM calls"
          value={llmCalls}
          description="Local model invocations"
        />

        <div className="rounded-lg border border-border p-3">
          <p className="font-mono text-xs uppercase tracking-widest text-faint">
            Processing
          </p>
          <p className="mt-2 text-2xl font-semibold">
            {processingLocation.toUpperCase()}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {localInference ? "Local inference enabled" : "Local inference unavailable"}
          </p>
        </div>

        <div className="rounded-lg border border-border p-3">
          <p className="font-mono text-xs uppercase tracking-widest text-faint">
            Models
          </p>
          <p className="mt-2 text-sm font-semibold">
            {modelsUsed}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Models used this run
          </p>
        </div>

        <div className="rounded-lg border border-border p-3">
          <p className="font-mono text-xs uppercase tracking-widest text-faint">
            Verification
          </p>
          <p className="mt-2 text-2xl font-semibold">
            {verificationStatus.toUpperCase()}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Final verification status
          </p>
        </div>
      </div>
    </section>
  );
}