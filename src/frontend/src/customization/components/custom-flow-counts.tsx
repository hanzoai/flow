import { ExternalLink } from "lucide-react";
import { useIamStore } from "@/stores/iamStore";

export function CustomFlowCounts() {
  const appUrl = useIamStore((state) => state.context?.links?.app) || "https://hanzo.app/flow";

  return (
    <a
      href={appUrl}
      target="_blank"
      rel="noreferrer"
      className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      data-testid="header-hanzo-app-link"
    >
      <span>Hanzo App</span>
      <ExternalLink className="h-3 w-3" />
    </a>
  );
}

export default CustomFlowCounts;
