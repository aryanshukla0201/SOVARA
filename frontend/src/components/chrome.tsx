import { Link, useRouterState } from "@tanstack/react-router";
import {
  BookOpen,
  Cpu,
  FileStack,
  Menu,
  Radio,
  Terminal,
  X,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import { Mark } from "@/components/mark";
import { SignedOut } from "@/lib/auth/gates";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/workbench", label: "Workbench", icon: Terminal },
  { to: "/fleet", label: "Fleet", icon: Cpu },
  { to: "/vault", label: "Vault", icon: BookOpen },
  { to: "/proof", label: "Proof", icon: Radio },
  { to: "/artifacts", label: "Artifacts", icon: FileStack },
] as const;

function isActive(path: string, to: string) {
  return path === to || path.startsWith(`${to}/`);
}

function useActivePath() {
  return useRouterState({ select: (s) => s.location.pathname });
}


export function Header() {
  const path = useActivePath();
  const [open, setOpen] = useState(false);

  return (
    <header className="relative z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/95 px-3 backdrop-blur-sm md:px-5">
      <Link to="/" className="flex items-center gap-2.5 pr-2">
        <Mark className="size-6" />
        <span className="font-display text-sm font-semibold tracking-wide">SOVARA</span>
      </Link>
      <nav className="ml-4 hidden items-center gap-1 lg:flex">
        {NAV.map((item) => {
          const active = isActive(path, item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "rounded-md px-3 py-2 text-sm transition-colors duration-150",
                active ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        {path === "/" ? (
          <SignedOut>
            <div className="hidden items-center gap-2 sm:flex">
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">Log in</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/signup">Sign up</Link>
              </Button>
            </div>
          </SignedOut>
        ) : null}
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X /> : <Menu />}
        </Button>
      </div>
      {open ? (
        <div className="absolute inset-x-0 top-14 border-b border-border bg-card p-3 lg:hidden">
          <nav className="grid gap-1">
            {NAV.map((item) => {
              const active = isActive(path, item.to);
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex h-11 items-center gap-3 rounded-md px-3 text-sm",
                    active ? "bg-secondary text-foreground" : "text-muted-foreground",
                  )}
                >
                  <Icon className="size-4" />
                  {item.label}
                </Link>
              );
            })}
            {path === "/" ? (
              <SignedOut>
                <div className="mt-2 grid gap-1 border-t border-border pt-2 sm:hidden">
                  <Link to="/login" onClick={() => setOpen(false)} className="flex h-11 items-center rounded-md px-3 text-sm text-muted-foreground">
                    Log in
                  </Link>
                  <Link to="/signup" onClick={() => setOpen(false)} className="flex h-11 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground">
                    Sign up
                  </Link>
                </div>
              </SignedOut>
            ) : null}
          </nav>
        </div>
      ) : null}
    </header>
  );
}

export function BottomNav() {
  const path = useActivePath();
  const items = NAV;
  return (
    <nav className="grid h-16 shrink-0 grid-cols-5 border-t border-border bg-card md:hidden">
      {items.map((item) => {
        const active = isActive(path, item.to);
        const Icon = item.icon;
        return (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              "flex flex-col items-center justify-center gap-1 text-xs tracking-wide",
              active ? "text-foreground" : "text-faint",
            )}
          >
            <Icon className="size-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Shell({
  children,
  mode = "page",
}: {
  children: ReactNode;
  mode?: "page" | "app";
}) {
  return (
    <div
      className={cn(
        "flex flex-col bg-background text-foreground",
        mode === "app" ? "h-dvh overflow-hidden" : "min-h-dvh",
      )}
    >
      <Header />
      <div className={cn("flex min-h-0 flex-1 flex-col", mode === "app" && "overflow-hidden")}>
        {children}
      </div>
    </div>
  );
}
