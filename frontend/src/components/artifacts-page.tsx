import { Download, FileSpreadsheet, FileText, Presentation, Terminal } from "lucide-react";
import { Shell } from "@/components/chrome";
import { Crop } from "@/components/crop";
import { Button } from "@/components/ui/button";
import {
  APPROVAL_NOTE_HTML,
  DELIVERABLES,
  EXCHANGER_PY,
  FINDINGS_CSV,
  SLIDES_HTML,
} from "@/lib/data";
import { downloadText } from "@/lib/download";

const ICONS = {
  note: FileText,
  sheet: FileSpreadsheet,
  slides: Presentation,
  code: Terminal,
} as const;

function handleDownload(id: string) {
  if (id === "note-h302") {
    downloadText("Approval_Note_H-302.doc", APPROVAL_NOTE_HTML, "application/msword");
  } else if (id === "sheet-h302") {
    downloadText("H-302_findings.csv", FINDINGS_CSV, "text/csv");
  } else if (id === "code-lmtd") {
    downloadText("exchanger_duty.py", EXCHANGER_PY, "text/x-python");
  } else if (id === "slides-ta") {
    downloadText("Turnaround_brief.html", SLIDES_HTML, "text/html");
  }
}

export function ArtifactsPage() {
  return (
    <Shell mode="page">
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <p className="font-mono text-xs uppercase tracking-widest text-ok">Deliverable Artifacts</p>
        <h1 className="mt-2 max-w-2xl font-display text-3xl font-medium tracking-tight md:text-4xl">
          Real files. Not a chat bubble.
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
          Notes, sheets, slides, and verified code written to the local vault. Download any
          artifact — they were composed on this box.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {DELIVERABLES.map((d) => {
            const Icon = ICONS[d.kind];
            return (
              <article key={d.id} className="flex flex-col rounded-xl border border-border bg-card p-5">
                <div className="flex items-start gap-3">
                  <span className="flex size-10 items-center justify-center rounded-md bg-secondary">
                    <Icon className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate text-sm font-medium">{d.name}</h2>
                    <p className="mt-0.5 font-mono text-xs text-faint">
                      {d.size} · {d.from}
                    </p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-4 self-start"
                  onClick={() => handleDownload(d.id)}
                >
                  <Download />
                  Download
                </Button>
              </article>
            );
          })}
        </div>

        <section className="mt-12 grid gap-6 lg:grid-cols-2">
          <Crop className="overflow-hidden rounded-xl bg-paper text-ink">
            <div className="border-b border-ink/15 px-5 py-3">
              <p className="font-mono text-xs uppercase tracking-widest text-ink/50">Preview · note</p>
              <p className="text-lg font-medium">Approval note — Fired heater H-302</p>
            </div>
            <div className="space-y-2 px-5 py-4 text-sm leading-relaxed">
              <p>
                <span className="font-medium">Recommendation.</span> Derate 8%, patch refractory this
                window, run an interim register sleeve from the site shop. Full-rate restart is not
                supported under OISD-STD-116.
              </p>
              <p className="text-ink/70">
                Prepared without egress. Sources: H-302 scan, OISD-STD-116, vendor correspondence.
              </p>
            </div>
          </Crop>
          <Crop className="overflow-hidden rounded-xl bg-elevated">
            <div className="border-b border-border px-5 py-3">
              <p className="font-mono text-xs uppercase tracking-widest text-faint">Preview · code</p>
              <p className="text-sm">exchanger_duty.py</p>
            </div>
            <pre className="overflow-x-auto px-5 py-4 font-mono text-xs leading-relaxed text-muted-foreground">
{`def lmtd(t1, t2, t3, t4):
    d1, d2 = t1 - t4, t2 - t3
    if abs(d1 - d2) < 1e-9:
        return d1
    return (d1 - d2) / log(d1 / d2)

# sandbox: 4 passed · egress 0`}
            </pre>
          </Crop>
        </section>
      </main>
    </Shell>
  );
}
