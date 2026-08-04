import { Button, DialogDescription, DialogHeader, DialogTitle, Label } from "@hanzo/ui";
import type { ProviderAccount } from "@/pages/MainPage/pages/deploymentsPage/types";

interface ProviderPhaseContentProps {
  providers: ProviderAccount[];
  selectedProviderId: string;
  onSelectProvider: (id: string) => void;
  onContinue: () => void;
  onCancel: () => void;
}

export default function ProviderPhaseContent({
  providers,
  selectedProviderId,
  onSelectProvider,
  onContinue,
  onCancel,
}: ProviderPhaseContentProps) {
  return (
    <>
      <DialogHeader>
        <DialogTitle>Select Provider</DialogTitle>
        <DialogDescription>
          Choose a provider environment to deploy to, or create a new deployment
          from scratch.
        </DialogDescription>
      </DialogHeader>

      <>
        {providers.map((provider) => (
          <div
            key={provider.id}
            className="flex items-center gap-3 rounded-lg border p-3"
          >
            
            <Label
              htmlFor={`provider-${provider.id}`}
              className="flex flex-1 cursor-pointer flex-col gap-0.5"
            >
              <span className="text-sm font-medium">{provider.name}</span>
              <span className="text-xs text-muted-foreground">
                {typeof provider.provider_data?.url === "string"
                  ? provider.provider_data.url
                  : "—"}
              </span>
            </Label>
          </div>
        ))}
      </>

      <div className="flex items-center justify-between pt-4">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={onContinue}>Continue</Button>
      </div>
    </>
  );
}
