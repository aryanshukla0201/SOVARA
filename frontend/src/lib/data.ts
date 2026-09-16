export type ModelId = "qwen-vl" | "qwen-coder" | "llama-reason" | "deepseek-r1";

export type Model = {
  id: ModelId;
  name: string;
  size: string;
  role: string;
  tasks: string[];
  vramGb: number;
  loaded: boolean;
  latency: string;
};

export const MODELS: Model[] = [
  {
    id: "qwen-vl",
    name: "Qwen2-VL 7B",
    size: "7B",
    role: "Drawings, scans, handwriting",
    tasks: ["vision", "ocr"],
    vramGb: 16,
    loaded: true,
    latency: "1.8 t/s vision",
  },
  {
    id: "qwen-coder",
    name: "Qwen2.5-Coder 32B",
    size: "32B",
    role: "Internal tools and calculations",
    tasks: ["code", "sandbox"],
    vramGb: 20,
    loaded: true,
    latency: "28 t/s",
  },
  {
    id: "llama-reason",
    name: "Llama 3.3 70B Instruct",
    size: "70B-Q4",
    role: "Notes, synthesis, policy",
    tasks: ["write", "plan", "retrieve"],
    vramGb: 40,
    loaded: true,
    latency: "18 t/s",
  },
  {
    id: "deepseek-r1",
    name: "DeepSeek-R1 Distill 14B",
    size: "14B",
    role: "Multi-step analysis",
    tasks: ["reason"],
    vramGb: 12,
    loaded: false,
    latency: "standby",
  },
];

export type VaultDoc = {
  id: string;
  title: string;
  fileName?: string;
  class: "Internal" | "Restricted" | "Standard";
  kind: string;
  uploaded: string;
  updated: string;
  pages: number;
  excerpt: string;
};

export const VAULT: VaultDoc[] = [
  {
    id: "oisd-116",
    title: "OISD-STD-116 Fire Protection Facilities",
    class: "Standard",
    kind: "Standard",
    uploaded: "2017-06",
    updated: "2017-06",
    pages: 84,
    excerpt:
      "Fired heaters shall maintain flame pattern within the designed firebox envelope. Air register malfunction is a reportable deviation.",
  },
  {
    id: "ta-sop",
    title: "Turnaround Isolation SOP — Unit 3",
    class: "Internal",
    kind: "SOP",
    uploaded: "2025-11",
    updated: "2025-11",
    pages: 41,
    excerpt:
      "Pump isolation requires suction and discharge blinds plus a tagged drain. P&ID hold points must be signed by the area authority.",
  },
  {
    id: "hex-manual",
    title: "Shell-and-tube exchanger design manual",
    class: "Internal",
    kind: "Manual",
    uploaded: "2024-02",
    updated: "2024-02",
    pages: 126,
    excerpt:
      "Duty Q = m · Cp · ΔT. LMTD correction Ft applies for multipass shells. Do not use arithmetic mean temperature difference.",
  },
  {
    id: "board-tpl",
    title: "Board note template — capital approval",
    class: "Restricted",
    kind: "Template",
    uploaded: "2026-01",
    updated: "2026-01",
    pages: 6,
    excerpt:
      "Heading, facts, options, recommendation, financial effect, residual risk. No vendor names in the open minute.",
  },
  {
    id: "pid-legend",
    title: "P&ID legend ISO 10628 — site overlay",
    class: "Internal",
    kind: "Drawing",
    uploaded: "2023-09",
    updated: "2023-09",
    pages: 12,
    excerpt:
      "Gate valves shown as bow-tie. Spectacle blinds indicated adjacent to isolation valves on pump suction.",
  },
  {
    id: "corr-2025",
    title: "Vendor correspondence — burner registers (redacted)",
    class: "Restricted",
    kind: "Mail",
    uploaded: "2025-12",
    updated: "2025-12",
    pages: 9,
    excerpt:
      "OEM lead time for H-302 burner 2 air register: 14 weeks. Site machine shop can fabricate an interim sleeve in 9 days.",
  },
];

export type LocalHost = {
  ip: string;
  name: string;
  role: string;
};

export const LOCAL_NET: LocalHost[] = [
  { ip: "10.12.0.10", name: "SOVARA-ops", role: "Workstation" },
  { ip: "10.12.0.4", name: "gpu-0", role: "llama.cpp" },
  { ip: "10.12.0.5", name: "gpu-1", role: "vLLM" },
  { ip: "10.12.0.8", name: "qdrant", role: "Vector index" },
  { ip: "10.12.0.9", name: "minio", role: "File vault" },
  { ip: "127.0.0.1", name: "sandbox", role: "Firecracker" },
];

export type Packet = {
  t: string;
  proto: string;
  src: string;
  dst: string;
  svc: string;
  bytes: number;
  action: "allow" | "deny";
};

export const SEED_PACKETS: Packet[] = [
  { t: "11:02:14", proto: "gRPC", src: "10.12.0.10", dst: "10.12.0.5:8000", svc: "vllm.complete", bytes: 18432, action: "allow" },
  { t: "11:02:14", proto: "HTTP", src: "10.12.0.10", dst: "10.12.0.8:6333", svc: "qdrant.search", bytes: 2204, action: "allow" },
  { t: "11:02:15", proto: "S3", src: "10.12.0.10", dst: "10.12.0.9:9000", svc: "minio.get", bytes: 482110, action: "allow" },
  { t: "11:02:16", proto: "gRPC", src: "10.12.0.10", dst: "10.12.0.4:50051", svc: "llava.ocr", bytes: 91002, action: "allow" },
];

export type Deliverable = {
  id: string;
  name: string;
  kind: "note" | "sheet" | "slides" | "code";
  size: string;
  from: string;
};

export const DELIVERABLES: Deliverable[] = [
  { id: "note-h302", name: "Approval_Note_H-302.doc", kind: "note", size: "18 KB", from: "Inspection demo" },
  { id: "sheet-h302", name: "H-302_findings.csv", kind: "sheet", size: "2 KB", from: "Inspection demo" },
  { id: "code-lmtd", name: "exchanger_duty.py", kind: "code", size: "4 KB", from: "Coding demo" },
  { id: "slides-ta", name: "Turnaround_brief.html", kind: "slides", size: "12 KB", from: "Vault synthesis" },
];

export type ScenarioId = "inspection" | "coding" | "pid";

export type ScenarioEvent =
  | { at: number; kind: "user"; text: string }
  | { at: number; kind: "route"; model: ModelId; reason: string }
  | { at: number; kind: "plan"; items: string[] }
  | { at: number; kind: "tool"; name: string; detail: string; status: "run" | "ok" }
  | { at: number; kind: "assistant"; text: string }
  | { at: number; kind: "artifact"; id: string }
  | { at: number; kind: "done" };

export type Scenario = {
  id: ScenarioId;
  title: string;
  blurb: string;
  taskType: string;
  prompt: string;
  events: ScenarioEvent[];
};

export const SCENARIOS: Scenario[] = [
  {
    id: "inspection",
    title: "Inspection scan → approval note",
    blurb: "Vision model reads a scanned heater report, grounds in OISD-STD-116, writes a Word note.",
    taskType: "Vision + write",
    prompt:
      "Read the scanned inspection report for fired heater H-302 from the April turnaround. Extract findings, check against OISD-STD-116, and draft an approval note for the plant manager.",
    events: [
      { at: 200, kind: "user", text: "Read the scanned inspection report for fired heater H-302 from the April turnaround. Extract findings, check against OISD-STD-116, and draft an approval note for the plant manager." },
      { at: 700, kind: "route", model: "qwen-vl", reason: "Task starts with a scanned PDF and handwritten margin notes. Vision first." },
      { at: 1100, kind: "plan", items: ["OCR the H-302 scan", "Ground findings in OISD-STD-116", "Draft plant-manager approval note", "Write Word + findings sheet"] },
      { at: 1600, kind: "tool", name: "vision.ocr", detail: "H-302_inspection_scan.pdf · 3 pages · handwriting layer", status: "run" },
      { at: 2800, kind: "tool", name: "vision.ocr", detail: "Extracted 14 findings · confidence 0.91", status: "ok" },
      { at: 3200, kind: "route", model: "llama-reason", reason: "Long-form note and policy language. Switching to Llama 3.3 70B." },
      { at: 3600, kind: "tool", name: "kb.search", detail: "OISD-STD-116 fired heater flame envelope", status: "run" },
      { at: 4400, kind: "tool", name: "kb.search", detail: "3 passages · vault hit, no external fetch", status: "ok" },
      { at: 5000, kind: "assistant", text: "H-302 is not in a fit state for full-rate restart. Three items sit outside the firebox envelope in OISD-STD-116: tube-skin +48°C on pass 3, refractory spall at peephole 4, and burner 2 air register locked at 30%. I recommend derate 8%, patch refractory this window, and fabricate an interim register sleeve (site shop, 9 days) while the OEM part is on 14-week lead. Approval note and findings sheet are on the bench." },
      { at: 5600, kind: "artifact", id: "note-h302" },
      { at: 5800, kind: "artifact", id: "sheet-h302" },
      { at: 6200, kind: "done" },
    ],
  },
  {
    id: "coding",
    title: "Exchanger duty in the sandbox",
    blurb: "Coder model writes Python, runs tests in a local Firecracker jail, returns a verified script.",
    taskType: "Code + sandbox",
    prompt:
      "Write a Python function for shell-and-tube duty and LMTD from the Unit 3 process data. Run tests in the sandbox. Do not call any network.",
    events: [
      { at: 200, kind: "user", text: "Write a Python function for shell-and-tube duty and LMTD from the Unit 3 process data. Run tests in the sandbox. Do not call any network." },
      { at: 700, kind: "route", model: "qwen-coder", reason: "Code generation and unit tests. Coder 32B selected over the general instruct model." },
      { at: 1100, kind: "plan", items: ["Read process data from vault", "Implement Q and LMTD", "Add Ft correction", "Run pytest in Firecracker"] },
      { at: 1500, kind: "tool", name: "files.read", detail: "vault://hex-manual §4.2 process data", status: "ok" },
      { at: 2000, kind: "tool", name: "sandbox.exec", detail: "python -m pytest exchanger_duty_test.py -q", status: "run" },
      { at: 3400, kind: "tool", name: "sandbox.exec", detail: "4 passed in 0.08s · egress syscalls: 0", status: "ok" },
      { at: 4000, kind: "assistant", text: "Duty for the given train is 4.82 MW. LMTD is 18.4 °C with Ft = 0.93 on the two-pass shell. Arithmetic mean would have overstated driving force by 11% — the sandbox test locks that in. Script is on the bench; nothing left the jail." },
      { at: 4600, kind: "artifact", id: "code-lmtd" },
      { at: 5000, kind: "done" },
    ],
  },
  {
    id: "pid",
    title: "P&ID isolation list",
    blurb: "Vision reads a drawing extract, vault SOP names the blinds, a tagged isolation list comes back.",
    taskType: "Vision + retrieve",
    prompt:
      "On this P&ID extract, identify isolation for pump P-101A. List blinds required and cite the Unit 3 isolation SOP.",
    events: [
      { at: 200, kind: "user", text: "On this P&ID extract, identify isolation for pump P-101A. List blinds required and cite the Unit 3 isolation SOP." },
      { at: 700, kind: "route", model: "qwen-vl", reason: "Engineering drawing. Vision model with P&ID legend overlay." },
      { at: 1100, kind: "plan", items: ["Read drawing symbols", "Identify P-101A envelope", "Match isolation SOP", "Emit tagged list"] },
      { at: 1600, kind: "tool", name: "vision.read_drawing", detail: "P101A_extract.png · ISO 10628 overlay", status: "run" },
      { at: 2600, kind: "tool", name: "vision.read_drawing", detail: "Suction GV-101A, discharge GV-102A, drain DV-14", status: "ok" },
      { at: 3000, kind: "route", model: "llama-reason", reason: "SOP citation and permit language." },
      { at: 3400, kind: "tool", name: "kb.search", detail: "Turnaround Isolation SOP — P-101A", status: "ok" },
      { at: 4100, kind: "assistant", text: "P-101A isolation: close GV-101A (suction) and GV-102A (discharge), open and tag DV-14 to drain, install spectacle blinds at both hold points. Area authority signature required before pull. Matches Unit 3 Isolation SOP §5.2. List exported to the Artifacts." },
      { at: 4700, kind: "done" },
    ],
  },
];

export const APPROVAL_NOTE_HTML = `<html><head><meta charset="utf-8"><title>Approval Note H-302</title>
<style>body{font-family:Calibri,Arial,sans-serif;max-width:720px;margin:40px auto;color:#1c1a16;line-height:1.45}h1{font-size:18px;letter-spacing:.08em;text-transform:uppercase}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:6px 8px;font-size:13px;text-align:left}.cls{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#666}</style></head>
<body>
<p class="cls">Internal · Western Refinery Complex · Unit 3</p>
<h1>Approval note — Fired heater H-302</h1>
<p>To: Plant Manager, Unit 3<br>From: Inspection cell / SOVARA workbench<br>Date: 7 September 2026<br>Subject: Restart fitness after April turnaround inspection</p>
<p><b>Facts.</b> Scanned report H-302 (3 pages, including handwritten margin notes) was read on-premises. Three deviations sit outside OISD-STD-116 firebox envelope:</p>
<ol>
<li>Tube-skin temperature +48°C above design on pass 3.</li>
<li>Refractory spalling at peephole 4.</li>
<li>Burner 2 air register locked at approximately 30% open; flame pattern irregular.</li>
</ol>
<p><b>Options.</b> (A) Full-rate restart — not supported. (B) Derate 8%, patch refractory this window, run with interim register sleeve from site shop (9 days) while OEM part is on 14-week lead. (C) Hold cold until OEM arrives.</p>
<p><b>Recommendation.</b> Option B. Residual risk: flame envelope still degraded until OEM register arrives; board should note the 8% throughput effect (~₹2.1 Cr / month) against a cold-hold cost several times higher.</p>
<p><b>Financial effect.</b> Interim sleeve: shop labour and material, within existing TA budget. OEM register: already in correspondence, no new commitment.</p>
<p>Prepared without egress from the premises. Sources: H-302 scan, OISD-STD-116, vendor correspondence (restricted).</p>
</body></html>`;

export const FINDINGS_CSV = `item,location,deviation,standard,action,window
1,Pass 3 tubes,Skin +48°C vs design,OISD-STD-116,Derate 8% and inspect at next pit stop,This run
2,Peephole 4,Refractory spall,OISD-STD-116,Patch this window,This TA
3,Burner 2,Air register locked 30%,OISD-STD-116,Interim sleeve 9 days; OEM 14 weeks,This TA`;

export const EXCHANGER_PY = `"""Shell-and-tube duty and LMTD. Local only."""
from math import log

def duty_mw(m_kg_s: float, cp_kj_kgk: float, dt_k: float) -> float:
    return m_kg_s * cp_kj_kgk * dt_k / 1000.0

def lmtd(t1: float, t2: float, t3: float, t4: float) -> float:
    d1 = t1 - t4
    d2 = t2 - t3
    if abs(d1 - d2) < 1e-9:
        return d1
    return (d1 - d2) / log(d1 / d2)

def ft_two_pass(R: float, P: float) -> float:
    # Simplified Bowman chart fit for 1-2 exchanger.
    return max(0.75, min(1.0, 1 - 0.08 * abs(R - 1) - 0.12 * (1 - P)))

if __name__ == "__main__":
    q = duty_mw(38.4, 2.45, 51.2)
    dt = lmtd(186, 134, 42, 98)
    print(round(q, 2), round(dt, 1), round(ft_two_pass(1.1, 0.62), 2))
`;

export const SLIDES_HTML = `<html><head><meta charset="utf-8"><title>Turnaround brief</title>
<style>body{margin:0;font-family:IBM Plex Sans,Arial,sans-serif;background:#08090a;color:#eceae4}section{min-height:100vh;padding:12vh 10vw;border-bottom:1px solid #2a2e2c}h1{font-weight:500;font-size:42px;letter-spacing:-.03em}p,li{font-size:20px;line-height:1.5;color:#b8bcb6} .k{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#8fad98}</style></head>
<body>
<section><p class="k">Unit 3 · Internal</p><h1>Turnaround briefing</h1><p>H-302 restart is conditional. Isolation of P-101A follows SOP §5.2. No material in this deck left the premises.</p></section>
<section><p class="k">Heater</p><h1>Derate 8% until OEM register.</h1><p>Patch refractory now. Site sleeve in 9 days. Throughput effect noted for the board.</p></section>
<section><p class="k">Pump</p><h1>P-101A blinds at GV-101A and GV-102A.</h1><p>Drain DV-14 tagged. Area authority to sign before pull.</p></section>
</body></html>`;

export function modelById(id: ModelId): Model {
  const found = MODELS.find((m) => m.id === id);
  if (!found) throw new Error(`unknown model ${id}`);
  return found;
}
