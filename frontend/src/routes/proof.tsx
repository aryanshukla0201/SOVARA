import { createFileRoute } from "@tanstack/react-router";
import { ProofPage } from "@/components/proof-page";

export const Route = createFileRoute("/proof")({ component: ProofPage });
