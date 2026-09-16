import { createFileRoute } from "@tanstack/react-router";
import { ArtifactsPage } from "@/components/artifacts-page";

export const Route = createFileRoute("/artifacts")({ component: ArtifactsPage });
