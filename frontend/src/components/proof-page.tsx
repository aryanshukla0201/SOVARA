import { ShieldOff } from "lucide-react";
import { useEffect, useState } from "react";
import { Shell } from "@/components/chrome";
import { Crop } from "@/components/crop";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LOCAL_NET, SEED_PACKETS, type Packet } from "@/lib/data";
import { cn } from "@/lib/utils";

const ROTATE: Omit<Packet, "t">[] = [
  { proto: "gRPC", src: "10.12.0.10", dst: "10.12.0.5:8000", svc: "vllm.complete", bytes: 8192, action: "allow" },
  { proto: "HTTP", src: "10.12.0.10", dst: "10.12.0.8:6333", svc: "qdrant.search", bytes: 1024, action: "allow" },
  { proto: "S3", src: "10.12.0.10", dst: "10.12.0.9:9000", svc: "minio.put", bytes: 24576, action: "allow" },
  { proto: "gRPC", src: "10.12.0.10", dst: "10.12.0.4:50051", svc: "vision.ocr", bytes: 4096, action: "allow" },
  { proto: "vsock", src: "127.0.0.1", dst: "127.0.0.1:5000", svc: "sandbox.exec", bytes: 512, action: "allow" },
];

function stamp() {
  const d = new Date();
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

export function ProofPage() {
  const [packets, setPackets] = useState<Packet[]>(SEED_PACKETS);
  const [probe, setProbe] = useState<"idle" | "deny">("idle");
  const [denied, setDenied] = useState(0);

  useEffect(() => {
    let i = 0;
    const id = window.setInterval(() => {
      const next = ROTATE[i % ROTATE.length];
      i += 1;
      setPackets((p) => [{ t: stamp(), ...next }, ...p].slice(0, 18));
    }, 1800);
    return () => window.clearInterval(id);
  }, []);

  function probeInternet() {
    setProbe("deny");
    setDenied((n) => n + 1);
    setPackets((p) => [
      {
        t: stamp(),
        proto: "HTTPS",
        src: "10.12.0.10",
        dst: "1.1.1.1:443",
        svc: "egress.probe",
        bytes: 0,
        action: "deny",
      },
      ...p,
    ]);
  }

  const allowed = packets.filter((p) => p.action === "allow").length;

  return (
    <Shell mode="page">
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <p className="font-mono text-xs uppercase tracking-widest text-ok">Sovereignty proof</p>
        <h1 className="mt-2 max-w-2xl font-display text-3xl font-medium tracking-tight md:text-4xl">
          External calls: zero. The log is the claim.
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
          Policy is deny-all egress. Only RFC1918, link-local, and loopback. Probe the public
          internet from this console — the packet is born already dead.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-widest text-faint">External</p>
            <p className="mt-2 font-display text-5xl font-medium tabular-nums leading-none">0</p>
            <p className="mt-2 text-sm text-ok">Destinations outside the fence</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-widest text-faint">Allowed local</p>
            <p className="mt-2 font-display text-5xl font-medium tabular-nums leading-none">{allowed}</p>
            <p className="mt-2 text-sm text-muted-foreground">This session, on-subnet only</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-widest text-faint">Denied probes</p>
            <p className="mt-2 font-display text-5xl font-medium tabular-nums leading-none">{denied}</p>
            <p className="mt-2 text-sm text-muted-foreground">Simulated HTTPS to 1.1.1.1</p>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button type="button" variant="outline" onClick={probeInternet}>
            <ShieldOff />
            Probe the public internet
          </Button>
          {probe === "deny" ? (
            <p className="text-sm text-crit">DENY · HTTPS 1.1.1.1:443 · policy default-drop</p>
          ) : (
            <p className="text-sm text-muted-foreground">Nothing here opens a public socket.</p>
          )}
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_20rem]">
          <section className="overflow-hidden rounded-xl border border-border">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <h2 className="text-sm font-medium">Packet log</h2>
              <Badge variant="ok">Live · local</Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-lg text-left font-mono text-xs">
                <thead className="text-faint">
                  <tr className="border-b border-border">
                    <th className="px-4 py-2 font-medium">Time</th>
                    <th className="px-2 py-2 font-medium">Proto</th>
                    <th className="px-2 py-2 font-medium">Dest</th>
                    <th className="px-2 py-2 font-medium">Service</th>
                    <th className="px-2 py-2 font-medium">Bytes</th>
                    <th className="px-4 py-2 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {packets.map((p, i) => (
                    <tr key={`${p.t}-${p.dst}-${i}`} className="border-b border-border/60">
                      <td className="px-4 py-2 tabular-nums text-muted-foreground">{p.t}</td>
                      <td className="px-2 py-2">{p.proto}</td>
                      <td className="px-2 py-2">{p.dst}</td>
                      <td className="px-2 py-2">{p.svc}</td>
                      <td className="px-2 py-2 tabular-nums">{p.bytes}</td>
                      <td className={cn("px-4 py-2 uppercase", p.action === "deny" ? "text-crit" : "text-ok")}>
                        {p.action}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="space-y-4">
            <Crop className="rounded-xl bg-card p-4">
              <p className="font-mono text-xs uppercase tracking-widest text-faint">Premises</p>
              <ul className="mt-3 space-y-2">
                {LOCAL_NET.map((h) => (
                  <li key={h.ip} className="flex items-center justify-between gap-2 text-sm">
                    <span>
                      <span className="block">{h.name}</span>
                      <span className="font-mono text-xs text-faint">{h.ip}</span>
                    </span>
                    <span className="text-xs text-muted-foreground">{h.role}</span>
                  </li>
                ))}
              </ul>
            </Crop>
            <div className="rounded-xl border border-dashed border-border p-4">
              <p className="font-mono text-xs uppercase tracking-widest text-faint">Policy</p>
              <p className="mt-2 font-mono text-xs leading-relaxed text-muted-foreground">
                ALLOW 10.0.0.0/8
                <br />
                ALLOW 172.16.0.0/12
                <br />
                ALLOW 192.168.0.0/16
                <br />
                ALLOW 127.0.0.0/8
                <br />
                DENY 0.0.0.0/0
              </p>
            </div>
          </aside>
        </div>
      </main>
    </Shell>
  );
}
