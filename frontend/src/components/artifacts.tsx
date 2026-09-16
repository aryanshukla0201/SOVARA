import { Crop } from "@/components/crop";

export function ScanDocument() {
  return (
    <Crop className="overflow-hidden rounded-md bg-paper text-ink">
      <div className="border-b border-ink/15 px-3 py-2">
        <p className="font-mono text-xs uppercase tracking-widest text-ink/55">
          Scan · H-302 · p.1/3
        </p>
        <p className="text-sm font-medium">Fired heater inspection</p>
      </div>
      <div className="space-y-1.5 px-3 py-3 text-xs leading-relaxed">
        <p>Unit 3 / April TA / Inspector: R. Menon</p>
        <p>Pass 3 tube skin: 48°C above design. Glow observed at peephole 4.</p>
        <p className="italic text-ink/70">margin: burner 2 register will not open past 30% — confirm with shop</p>
        <p>Flame pattern irregular. Recommend derate pending repair.</p>
      </div>
    </Crop>
  );
}

export function PidDrawing() {
  return (
    <Crop className="overflow-hidden rounded-md bg-elevated">
      <p className="border-b border-border px-3 py-2 font-mono text-xs uppercase tracking-widest text-faint">
        P&ID extract · P-101A
      </p>
      <svg viewBox="0 0 280 140" className="h-36 w-full text-primary" aria-label="P and ID extract for pump P-101A">
        <rect x="8" y="8" width="264" height="124" fill="none" stroke="currentColor" opacity="0.2" />
        <line x1="20" y1="70" x2="70" y2="70" stroke="currentColor" strokeWidth="1.5" />
        <polygon points="70,62 86,70 70,78" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <text x="64" y="54" fontSize="8" fill="currentColor">
          GV-101A
        </text>
        <circle cx="120" cy="70" r="16" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <text x="108" y="74" fontSize="8" fill="currentColor">
          P-101A
        </text>
        <polygon points="154,62 170,70 154,78" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <text x="148" y="54" fontSize="8" fill="currentColor">
          GV-102A
        </text>
        <line x1="170" y1="70" x2="250" y2="70" stroke="currentColor" strokeWidth="1.5" />
        <line x1="120" y1="86" x2="120" y2="114" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="120" cy="120" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <text x="132" y="124" fontSize="8" fill="currentColor">
          DV-14
        </text>
        <rect x="78" y="64" width="10" height="12" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <rect x="172" y="64" width="10" height="12" fill="none" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    </Crop>
  );
}
