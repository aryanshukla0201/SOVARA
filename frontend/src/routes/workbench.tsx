import { createFileRoute } from "@tanstack/react-router";
import { WorkbenchPage } from "@/components/workbench-page";

type WorkbenchSearch = {
  demo?: string;
};

export const Route = createFileRoute("/workbench")({
  validateSearch: (search: Record<string, unknown>): WorkbenchSearch => ({
    demo: typeof search.demo === "string" ? search.demo : undefined,
  }),
  component: WorkbenchRoute,
});

function WorkbenchRoute() {
  const { demo } = Route.useSearch();
  return <WorkbenchPage demo={demo} />;
}
