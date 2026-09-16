import { cn } from "@/lib/utils";

export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn("text-primary", className)} aria-hidden>
      <path
        d="M12 2.5 L20.5 6 v7.2 c0 5.2-8.5 10.3-8.5 10.3S3.5 18.4 3.5 13.2 V6 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="miter"
      />
      <path d="M12 8 v8" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8.5 12.2 h7" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
