import { createFileRoute } from "@tanstack/react-router";
import { FleetPage } from "@/components/fleet-page";

export const Route = createFileRoute("/fleet")({ component: FleetPage });
