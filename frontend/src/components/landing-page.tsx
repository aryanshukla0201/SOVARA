import { Link } from "@tanstack/react-router";
import { ArrowRight, Lock, ScanLine, Server } from "lucide-react";
import { Shell } from "@/components/chrome";
import { Crop } from "@/components/crop";
import {
  MockDesktop,
  MockPhone,
  MockPipeline,
  MockProof,
  MockRouter,
  MockTablet,
} from "@/components/device-mocks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SPECIMENS = [
  { id: "phone", label: "Phone · 390", hint: "Single pane, bottom nav, 44px composer.", node: <MockPhone /> },
  { id: "tablet", label: "Tablet · 768", hint: "Chat plus a sliding plan rail.", node: <MockTablet /> },
  { id: "desktop", label: "Desktop · 1280", hint: "Threads, agent, and egress proof.", node: <MockDesktop /> },
] as const;

const GALLERY = [
  {
    to: "/workbench" as const,
    search: undefined,
    title: "Command deck",
    copy: "Three-pane operator console. Plan, tools, files, and the agent in one surface.",
    node: <MockDesktop />,
  },
  {
    to: "/workbench" as const,
    search: { demo: "inspection" },
    title: "Inspection pipeline",
    copy: "Scan to OCR to grounded note. The flagship multimodal loop.",
    node: <MockPipeline />,
  },
  {
    to: "/fleet" as const,
    search: undefined,
    title: "Model router",
    copy: "Coding, vision, and long-form writing pick different open-weight models.",
    node: <MockRouter />,
  },
  {
    to: "/proof" as const,
    search: undefined,
    title: "Sovereignty proof",
    copy: "Live local packet log. External calls stay at zero — visible, not claimed.",
    node: <MockProof />,
  },
  {
    to: "/workbench" as const,
    search: { demo: "coding" },
    title: "Sandbox coding",
    copy: "Script, test, and verify inside Firecracker. No outbound syscalls.",
    node: <MockDesktop />,
  },
  {
    to: "/vault" as const,
    search: undefined,
    title: "Knowledge vault",
    copy: "SOPs, OISD, drawings, correspondence. Retrieval never leaves the subnet.",
    node: <MockTablet />,
  },
];

const PILLARS = [
  {
    icon: Lock,
    title: "Air-gapped by design",
    copy: "Inference, OCR, search, and file write all bind to RFC1918 and loopback. The proof page is the claim.",
  },
  {
    icon: Server,
    title: "A fleet, not a model",
    copy: "Vision, coder, and instruct weights sit side by side. New open-weight models drop in without a redesign.",
  },
  {
    icon: ScanLine,
    title: "Deliverables, not chat",
    copy: "Approval notes, sheets, slides, and verified code. The agent iterates with local tools until the file exists.",
  },
] as const;

export function LandingPage() {
  return (
    <Shell mode="page">
      <main>
        <section className="grid-drawing relative border-b border-border">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 md:px-6 md:py-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-end lg:py-20">
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-ok">
                Sovereign · On-premise · Open-weight
              </p>
              <h1 className="mt-4 max-w-xl font-display text-4xl font-medium leading-tight tracking-tight md:text-5xl lg:text-6xl">
                Sovereign Orchestration for Verified AI Reasoning & Automation.
              </h1>
              <p className="mt-5 max-w-lg text-base leading-relaxed text-muted-foreground md:text-lg">
                Refineries, PSUs, defence production, secretariat notes. SOVARA runs
                the agent on your GPU — scanned drawings, SOPs, and code included —
                and never opens a socket past the plant network.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="lg">
                  <Link to="/workbench">
                    Open workbench
                    <ArrowRight />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link to="/workbench" search={{ demo: "inspection" }}>
                    Run inspection demo
                  </Link>
                </Button>
              </div>
            </div>
            <Crop className="hidden h-72 lg:block">
              <MockDesktop />
            </Crop>
          </div>
        </section>

        <section className="border-b border-border">
          <div className="mx-auto grid max-w-6xl gap-px bg-border md:grid-cols-3">
            {PILLARS.map((p) => (
              <article key={p.title} className="bg-background px-5 py-8 md:px-8">
                <p.icon className="size-5 text-primary" />
                <h2 className="mt-4 text-lg font-medium">{p.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.copy}</p>
              </article>
            ))}
          </div>
        </section>


        <section className="py-14 md:py-20">
          <div className="mx-auto max-w-6xl px-4 md:px-6">
            <p className="font-mono text-xs uppercase tracking-widest text-faint">Prototype gallery</p>
            <h2 className="mt-2 font-display text-3xl font-medium tracking-tight md:text-4xl">
              Six surfaces. One premises.
            </h2>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {GALLERY.map((g) => (
                <Link
                  key={g.title}
                  to={g.to}
                  search={g.search}
                  className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card transition-colors duration-200 hover:border-foreground/25"
                >
                  <div className="h-40 p-3">{g.node}</div>
                  <div className="flex flex-1 flex-col gap-2 border-t border-border p-4">
                    <h3 className="flex items-center justify-between text-base font-medium">
                      {g.title}
                      <ArrowRight className="size-4 text-faint transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-foreground" />
                    </h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{g.copy}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <footer className="border-t border-border py-8">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
            <p>SOVARA · prototype for on-prem GPU servers. No cloud inference.</p>
            <p className="font-mono text-xs uppercase tracking-widest">Where sovereignty meets intelligence.</p>
          </div>
        </footer>
      </main>
    </Shell>
  );
}
