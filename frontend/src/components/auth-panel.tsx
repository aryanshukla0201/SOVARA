import { Link } from "@tanstack/react-router";
import { ArrowRight, Check, Eye, EyeOff, LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { GROK_PROVIDERS, authClient, authEnabled, signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { cn } from "@/lib/utils";

export type AuthMode = "login" | "signup";

type AuthPanelProps = {
  mode?: AuthMode;
  compact?: boolean;
  callbackURL?: string;
};

const BENEFITS = ["Run private workloads on your GPU", "Keep files and inference inside the plant network"];

export function AuthPanel({ mode = "login", compact = false, callbackURL = "/workbench" }: AuthPanelProps) {
  const { user, isPending } = useCurrentUserState();
  const [activeMode, setActiveMode] = useState<AuthMode>(mode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (isPending) {
    return <div className={cn("animate-pulse rounded-xl border border-border bg-card", compact ? "h-64" : "h-96")} />;
  }

  if (user) {
    return (
      <div className="rounded-xl border border-border bg-card p-5 md:p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ok">Session active</p>
        <h2 className="mt-3 font-display text-2xl font-medium tracking-tight">Welcome back, {user.displayName ?? "operator"}.</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">Your SOVARA workspace is ready for private work.</p>
        <Button asChild className="mt-5">
          <Link to={callbackURL}>
            Open workbench
            <ArrowRight />
          </Link>
        </Button>
      </div>
    );
  }

  async function handleCredentials(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!authEnabled) {
      setError("Sign-in is not enabled in this environment yet.");
      return;
    }
    if (password.length < 8) {
      setError("Use a password with at least 8 characters.");
      return;
    }
    setPending("credentials");
    try {
      const result = activeMode === "login"
        ? await authClient.signIn.email({ email, password, callbackURL })
        : await authClient.signUp.email({ name: name.trim(), email, password, callbackURL });
      if (result.error) throw new Error(result.error.message ?? "Unable to complete authentication.");
      window.location.href = callbackURL;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to complete authentication.");
      setPending(null);
    }
  }

  async function handleProvider(providerId: string) {
    setError("");
    setPending(providerId);
    try {
      await signIn(providerId, { callbackURL, errorCallbackURL: activeMode === "login" ? "/login" : "/signup" });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to open provider sign-in.");
      setPending(null);
    }
  }

  return (
    <div className={cn("rounded-xl border border-border bg-card", compact ? "p-5" : "p-6 md:p-8")}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-ok">Operator access</p>
          <h2 className="mt-2 font-display text-2xl font-medium tracking-tight">
            {activeMode === "login" ? "Return to the command deck." : "Create your operator account."}
          </h2>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
            {activeMode === "login" ? "Resume secure, on-premise AI workflows." : "Set up a secure identity for your private workspace."}
          </p>
        </div>
        <div className="hidden rounded-lg border border-border bg-elevated p-2 sm:block">
          <LockKeyhole className="size-5 text-ok" />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 rounded-lg bg-secondary p-1 text-sm">
        {(["login", "signup"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => { setActiveMode(tab); setError(""); }}
            className={cn("rounded-md px-3 py-2 transition-colors", activeMode === tab ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
          >
            {tab === "login" ? "Log in" : "Sign up"}
          </button>
        ))}
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {GROK_PROVIDERS.map((provider) => (
          <Button key={provider.providerId} type="button" variant="outline" disabled={pending !== null} onClick={() => void handleProvider(provider.providerId)}>
            {pending === provider.providerId ? <LoaderCircle className="animate-spin" /> : null}
            Continue with {provider.label}
          </Button>
        ))}
      </div>

      <div className="my-5 flex items-center gap-3 text-xs text-faint">
        <span className="h-px flex-1 bg-border" />
        <span>or use email</span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <form className="grid gap-3" onSubmit={handleCredentials}>
        {activeMode === "signup" ? (
          <label className="grid gap-1.5 text-sm">
            <span className="text-muted-foreground">Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} required autoComplete="name" className="h-11 rounded-md border border-input bg-background px-3 outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20" />
          </label>
        ) : null}
        <label className="grid gap-1.5 text-sm">
          <span className="text-muted-foreground">Work email</span>
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" className="h-11 rounded-md border border-input bg-background px-3 outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20" />
        </label>
        <label className="grid gap-1.5 text-sm">
          <span className="text-muted-foreground">Password</span>
          <span className="relative">
            <input type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete={activeMode === "login" ? "current-password" : "new-password"} className="h-11 w-full rounded-md border border-input bg-background px-3 pr-11 outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20" />
            <button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)} className="absolute inset-y-0 right-0 grid w-11 place-items-center text-muted-foreground hover:text-foreground">
              {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </span>
        </label>
        {error ? <p role="alert" className="rounded-md border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit">{error}</p> : null}
        <Button type="submit" disabled={pending !== null} className="mt-1 h-11">
          {pending === "credentials" ? <LoaderCircle className="animate-spin" /> : null}
          {activeMode === "login" ? "Log in securely" : "Create account"}
        </Button>
      </form>

      <div className="mt-5 flex items-start gap-2 border-t border-border pt-4 text-xs leading-relaxed text-faint">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-ok" />
        <span>Your identity is used for workspace access. Inference and files stay on-premise.</span>
      </div>

      {!compact ? (
        <div className="mt-5 grid gap-2 text-xs text-muted-foreground">
          {BENEFITS.map((benefit) => <p key={benefit} className="flex items-center gap-2"><Check className="size-3.5 text-ok" />{benefit}</p>)}
        </div>
      ) : null}
    </div>
  );
}
