import { Crop } from "@/components/crop";
import { Mark } from "@/components/mark";
import { cn } from "@/lib/utils";

function MiniBar({ right = "Sealed" }: { right?: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-2.5 py-1.5">
      <Mark className="size-3.5" />
      <span className="text-xs font-medium">SOVARA</span>
      <span className="ml-auto flex items-center gap-1 font-mono text-xs text-ok">
        <span className="led-ok size-1.5 rounded-full bg-ok" />
        {right}
      </span>
    </div>
  );
}

export function MockPhone() {
  return (
    <Crop className="relative h-full overflow-hidden rounded-xl bg-card">
      <MiniBar />
      <div className="flex h-full flex-col gap-2 p-2.5 pb-12">
        <div className="self-end max-w-[85%] rounded-md rounded-br-sm bg-secondary px-2 py-1.5 text-xs leading-snug">
          Read the H-302 scan and draft the approval note.
        </div>
        <div className="rounded-md border border-ok/30 bg-ok/10 px-2 py-1.5 text-xs text-ok">
          Routed · Qwen2-VL → Llama 70B
        </div>
        <div className="max-w-[95%] rounded-md rounded-bl-sm border border-border px-2 py-1.5 text-xs leading-snug text-foreground/90">
          Three envelope deviations. Derate 8%. Note on the bench.
        </div>
        <div className="rounded-sm border border-dashed border-border px-2 py-1.5 font-mono text-xs text-faint">
          Approval_Note_H-302.doc
        </div>
        <div className="mt-auto flex h-8 items-center rounded-md border border-border bg-secondary px-2 text-xs text-faint">
          Task the agent
        </div>
      </div>
      <div className="absolute inset-x-0 bottom-0 grid grid-cols-5 border-t border-border bg-card py-1.5">
        {["Work", "Fleet", "Vault", "Proof", "Files"].map((l, i) => (
          <span
            key={l}
            className={cn("text-center font-mono text-xs", i === 0 ? "text-foreground" : "text-faint")}
          >
            {l}
          </span>
        ))}
      </div>
    </Crop>
  );
}

export function MockTablet() {
  return (
    <Crop className="flex h-full flex-col overflow-hidden rounded-xl bg-card">
      <MiniBar right="Qwen2-VL" />
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
          <div className="self-end max-w-[75%] rounded-md bg-secondary px-2.5 py-1.5 text-xs">
            Isolate P-101A from this drawing.
          </div>
          <div className="w-4/5 rounded-md border border-border px-2.5 py-1.5 text-xs leading-relaxed text-muted-foreground">
            GV-101A · GV-102A · DV-14 · blinds at both holds. SOP §5.2.
          </div>
          <div className="mt-auto h-9 rounded-md border border-border bg-secondary px-2 py-2 text-xs text-faint">
            Task the agent
          </div>
        </div>
        <aside className="flex w-32 shrink-0 flex-col gap-2 border-l border-border p-2">
          <span className="font-mono text-xs uppercase tracking-widest text-faint">Plan</span>
          {["Read drawing", "Match SOP", "List blinds"].map((s, i) => (
            <span key={s} className="rounded-sm bg-secondary px-1.5 py-1 text-xs text-muted-foreground">
              {i + 1} {s}
            </span>
          ))}
        </aside>
      </div>
    </Crop>
  );
}

export function MockDesktop() {
  return (
    <Crop className="flex h-full flex-col overflow-hidden rounded-xl bg-card">
      <MiniBar right="Sealed · 0 egress" />
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-28 flex-col gap-1 border-r border-border p-2 md:flex">
          <span className="font-mono text-xs uppercase tracking-widest text-faint">Threads</span>
          {["H-302 note", "Duty calc", "P-101A"].map((t, i) => (
            <span
              key={t}
              className={cn(
                "rounded-sm px-1.5 py-1 text-xs",
                i === 0 ? "bg-secondary text-foreground" : "text-muted-foreground",
              )}
            >
              {t}
            </span>
          ))}
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1 gap-0">
            <div className="flex min-w-0 flex-1 flex-col gap-2 p-3">
              <div className="self-end max-w-[80%] rounded-md bg-secondary px-2 py-1.5 text-xs">
                Draft the H-302 approval note from the scan.
              </div>
              <div className="rounded-md border border-ok/30 bg-ok/10 px-2 py-1 text-xs text-ok">
                Llama 3.3 70B · policy write
              </div>
              <div className="rounded-md border border-border px-2 py-1.5 text-xs leading-snug text-muted-foreground">
                Derate 8%. Patch refractory. Interim sleeve in 9 days.
              </div>
            </div>
            <div className="hidden w-28 flex-col justify-between border-l border-border p-2 lg:flex">
              <span className="font-mono text-xs uppercase tracking-widest text-faint">Egress</span>
              <span>
                <span className="font-display text-2xl font-medium leading-none">0</span>
                <span className="mt-1 block text-xs text-ok">No external</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </Crop>
  );
}

export function MockRouter() {
  return (
    <Crop className="flex h-full flex-col gap-2 overflow-hidden rounded-xl bg-card p-3">
      <span className="font-mono text-xs uppercase tracking-widest text-faint">Auto-select</span>
      <div className="grid flex-1 grid-cols-2 gap-2">
        {[
          ["Scan", "Qwen2-VL"],
          ["Note", "Llama 70B"],
          ["Code", "Coder 32B"],
          ["Reason", "R1 14B"],
        ].map(([k, v]) => (
          <div key={k} className="flex flex-col justify-between rounded-md border border-border bg-elevated p-2">
            <span className="text-xs text-muted-foreground">{k}</span>
            <span className="text-xs font-medium">{v}</span>
          </div>
        ))}
      </div>
    </Crop>
  );
}

export function MockPipeline() {
  const steps = ["Scan", "OCR", "Ground", "Note"];
  return (
    <Crop className="flex h-full flex-col justify-center gap-3 overflow-hidden rounded-xl bg-card p-4">
      <div className="flex items-center gap-1">
        {steps.map((s, i) => (
          <div key={s} className="flex min-w-0 flex-1 items-center gap-1">
            <div
              className={cn(
                "flex h-8 min-w-0 flex-1 items-center justify-center rounded-sm text-xs",
                i < 3 ? "bg-ok/15 text-ok" : "bg-secondary text-muted-foreground",
              )}
            >
              {s}
            </div>
            {i < steps.length - 1 ? <span className="shrink-0 text-faint">→</span> : null}
          </div>
        ))}
      </div>
      <div className="h-20 rounded-md bg-paper p-2 text-ink">
        <p className="font-mono text-xs uppercase tracking-widest">H-302 scan</p>
        <p className="mt-1 text-xs leading-snug">Pass 3 skin +48°C. Register 2 stuck.</p>
      </div>
    </Crop>
  );
}

export function MockProof() {
  return (
    <Crop className="flex h-full flex-col overflow-hidden rounded-xl bg-card p-3">
      <div className="flex items-end justify-between">
        <span className="font-mono text-xs uppercase tracking-widest text-faint">External</span>
        <span className="font-display text-3xl font-medium leading-none">0</span>
      </div>
      <p className="mt-1 text-xs text-ok">All traffic inside 10.12.0.0/16</p>
      <div className="mt-3 space-y-1 font-mono text-xs text-muted-foreground">
        <p>gRPC  10.12.0.5  vllm</p>
        <p>HTTP  10.12.0.8  qdrant</p>
        <p>S3    10.12.0.9  minio</p>
        <p className="text-crit">DENY  1.1.1.1  egress</p>
      </div>
    </Crop>
  );
}
