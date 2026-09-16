import { ArrowRight } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Shell } from "@/components/chrome";
import { Crop } from "@/components/crop";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MODELS, SCENARIOS } from "@/lib/data";
import { cn } from "@/lib/utils";

const ROUTES = [
  {
    task: "Scanned report, P&ID, handwriting",
    need: "Vision + OCR",
    pick: "Qwen2-VL 7B",
    demo: "inspection" as const,
  },
  {
    task: "Python, tests, internal tools",
    need: "Code + sandbox",
    pick: "Qwen2.5-Coder 32B",
    demo: "coding" as const,
  },
  {
    task: "Approval note, SOP citation",
    need: "Long-form + retrieval",
    pick: "Llama 3.3 70B",
    demo: "inspection" as const,
  },
];

export function FleetPage() {
  const used = MODELS.filter((m) => m.loaded).reduce((n, m) => n + m.vramGb, 0);

  return (
    <Shell mode="page">
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <p className="font-mono text-xs uppercase tracking-widest text-ok">Model fleet</p>
        <h1 className="mt-2 max-w-2xl font-display text-3xl font-medium tracking-tight md:text-4xl">
          Auto-select across task types. Swap weights without a redesign.
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
          The router reads the task, not a brand. Vision, coder, and instruct sit on the same
          mid-range box. A new open-weight model is a config row.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <Stat label="Loaded" value={`${MODELS.filter((m) => m.loaded).length} / ${MODELS.length}`} />
          <Stat label="VRAM in use" value={`${used} GB`} hint="of 80 GB dual GPU" />
          <Stat label="External APIs" value="0" hint="weights on disk" />
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-2">
          {MODELS.map((m) => (
            <article key={m.id} className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-medium">{m.name}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{m.role}</p>
                </div>
                <Badge variant={m.loaded ? "ok" : "default"}>{m.loaded ? "Loaded" : "Standby"}</Badge>
              </div>
              <dl className="mt-4 grid grid-cols-3 gap-2 font-mono text-xs uppercase tracking-wider text-faint">
                <div>
                  <dt>Size</dt>
                  <dd className="mt-1 text-foreground">{m.size}</dd>
                </div>
                <div>
                  <dt>VRAM</dt>
                  <dd className="mt-1 text-foreground">{m.vramGb} GB</dd>
                </div>
                <div>
                  <dt>Pace</dt>
                  <dd className="mt-1 text-foreground">{m.latency}</dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {m.tasks.map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            </article>
          ))}
        </div>

        <section className="mt-14">
          <h2 className="font-display text-2xl font-medium tracking-tight">Router map</h2>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Same prompt box, three paths. Run any of them on the workbench to watch the switch.
          </p>
          <div className="mt-6 overflow-hidden rounded-xl border border-border">
            {ROUTES.map((r, i) => (
              <Link
                key={r.task}
                to="/workbench"
                search={{ demo: r.demo }}
                className={cn(
                  "flex flex-col gap-2 px-4 py-4 transition-colors duration-150 hover:bg-secondary/50 sm:flex-row sm:items-center sm:gap-6",
                  i > 0 && "border-t border-border",
                )}
              >
                <span className="flex-1 text-sm">{r.task}</span>
                <span className="font-mono text-xs uppercase tracking-widest text-faint">{r.need}</span>
                <span className="flex items-center gap-2 text-sm font-medium">
                  {r.pick}
                  <ArrowRight className="size-4 text-faint" />
                </span>
              </Link>
            ))}
          </div>
          <Crop className="mt-6 hidden rounded-xl bg-elevated p-5 md:block">
            <p className="font-mono text-xs uppercase tracking-widest text-faint">Decision</p>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              classify(task) → capabilities[] → first loaded model that covers the set →
              fallback to instruct. Adding a 120B-class weight is a registry insert; the
              workbench does not care who trained it, only that it never calls out.
            </p>
          </Crop>
          <Button asChild className="mt-6">
            <Link to="/workbench" search={{ demo: "coding" }}>
              Watch a coding route
            </Link>
          </Button>
        </section>
      </main>
    </Shell>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-4">
      <p className="font-mono text-xs uppercase tracking-widest text-faint">{label}</p>
      <p className="mt-2 font-display text-3xl font-medium tabular-nums leading-none">{value}</p>
      {hint ? <p className="mt-2 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
