import { CircleUserRound, LogOut, Settings2, SlidersHorizontal, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { signOut } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { cn } from "@/lib/utils";

type ProfileMenuProps = {
  fallback: {
    name: string;
    role: string;
    org: string;
  };
};

const OPTIONS = [
  { label: "Account", icon: CircleUserRound },
  { label: "Profile", icon: UserRound },
  { label: "Settings", icon: Settings2 },
];

export function WorkbenchProfileMenu({ fallback }: ProfileMenuProps) {
  const { user } = useCurrentUserState();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [notice, setNotice] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);

  const name = user?.displayName ?? fallback.name;
  const email = user?.primaryEmail;
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function handleSignOut() {
    setSigningOut(true);
    void signOut().catch(() => setSigningOut(false));
  }

  function handleOption(label: string) {
    setNotice(`${label} controls are available for this workspace.`);
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between rounded-md px-1 py-1.5 text-left transition-colors duration-150 hover:bg-secondary/50 focus-visible:bg-secondary/50"
      >
        <span className="flex min-w-0 items-center gap-2">
          {user?.profileImageUrl ? (
            <img src={user.profileImageUrl} alt="" className="size-8 shrink-0 rounded-full object-cover" />
          ) : (
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary font-mono text-xs font-medium text-primary">
              {initials}
            </span>
          )}
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{name}</span>
            <span className="block truncate text-xs text-faint">{user?.primaryEmail ?? fallback.role}</span>
          </span>
        </span>
        <SlidersHorizontal className={cn("size-4 shrink-0 text-faint transition-transform", open && "rotate-90 text-foreground")} />
      </button>

      {open ? (
        <div className="absolute inset-x-0 bottom-full z-30 mb-2 rounded-xl border border-border bg-card/98 p-2 shadow-2xl shadow-black/40 backdrop-blur-md" role="menu">
          <div className="border-b border-border px-2 pb-2">
            <p className="text-sm font-medium">{name}</p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{email ?? fallback.org}</p>
          </div>
          <div className="mt-1 grid gap-0.5">
            {OPTIONS.map((option) => {
              const Icon = option.icon;
              return (
                <button
                  key={option.label}
                  type="button"
                  role="menuitem"
                  onClick={() => handleOption(option.label)}
                  className="flex h-10 w-full items-center gap-2 rounded-md px-2 text-left text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <Icon className="size-4" />
                  {option.label}
                </button>
              );
            })}
          </div>
          {notice ? <p className="mt-2 rounded-md bg-elevated px-2 py-1.5 text-xs text-faint">{notice}</p> : null}
          <div className="mt-1 border-t border-border pt-1">
            <button
              type="button"
              role="menuitem"
              disabled={signingOut}
              onClick={handleSignOut}
              className="flex h-10 w-full items-center gap-2 rounded-md px-2 text-sm text-crit transition-colors hover:bg-crit/10 disabled:cursor-wait disabled:opacity-60"
            >
              <LogOut className="size-4" />
              {signingOut ? "Logging out…" : "Log out"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
