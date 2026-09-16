import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Crop({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute -left-px -top-px size-2.5 border-l border-t border-foreground/35" />
      <span className="pointer-events-none absolute -right-px -top-px size-2.5 border-r border-t border-foreground/35" />
      <span className="pointer-events-none absolute -bottom-px -left-px size-2.5 border-b border-l border-foreground/35" />
      <span className="pointer-events-none absolute -bottom-px -right-px size-2.5 border-b border-r border-foreground/35" />
      <div className={cn(className)}>{children}</div>
    </div>
  );
}
