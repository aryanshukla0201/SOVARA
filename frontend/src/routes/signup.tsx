import { createFileRoute } from "@tanstack/react-router";
import { AuthPanel } from "@/components/auth-panel";
import { Shell } from "@/components/chrome";

export const Route = createFileRoute("/signup")({ component: SignupPage });

function SignupPage() {
  return (
    <Shell mode="page">
      <main className="grid min-h-[calc(100dvh-3.5rem)] items-center px-4 py-10 md:px-6">
        <div className="mx-auto grid w-full max-w-5xl gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <section className="hidden lg:block">
            <p className="font-mono text-xs uppercase tracking-widest text-ok">SOVARA / new operator</p>
            <h1 className="mt-4 max-w-md font-display text-5xl font-medium leading-tight tracking-tight">Bring trusted reasoning to the plant floor.</h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">Create your access profile and keep every model, document, and decision within your own perimeter.</p>
          </section>
          <AuthPanel mode="signup" />
        </div>
      </main>
    </Shell>
  );
}
