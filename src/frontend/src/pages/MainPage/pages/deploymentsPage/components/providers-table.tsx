import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@hanzo/ui";
import { Spinner } from "@hanzo/gui";
import { cn } from "@/utils/utils";
import type { ProviderAccount } from "../types";

interface ProvidersTableProps {
  providers: ProviderAccount[];
  deletingId?: string | null;
  onDeleteProvider?: (provider: ProviderAccount) => void;
}

function truncateMiddle(text: string, maxLength = 50): string {
  if (text.length <= maxLength) return text;
  const half = Math.floor((maxLength - 3) / 2);
  return `${text.slice(0, half)}...${text.slice(-half)}`;
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ProvidersTable({
  providers,
  deletingId,
  onDeleteProvider,
}: ProvidersTableProps) {
  return (
    <>
      <>
        <>
          <>Name</>
          <>URL</>
          <>Provider Key</>
          <>Created</>
          
        </>
      </>
      <>
        {providers.map((provider) => {
          const isDeleting = deletingId === provider.id;
          return (
            <>
              <>
                <span className="font-medium">{provider.name}</span>
              </>
              <>
                <span className="text-sm text-muted-foreground">
                  {typeof provider.provider_data?.url === "string"
                    ? truncateMiddle(provider.provider_data.url)
                    : "—"}
                </span>
              </>
              <>
                <span className="text-sm">{provider.provider_key}</span>
              </>
              <>
                <span className="text-sm">
                  {formatDate(provider.created_at)}
                </span>
              </>
              <>
                {isDeleting ? (
                  <div className="flex h-8 w-8 items-center justify-center">
                    <Spinner size={16} className="text-muted-foreground" />
                  </div>
                ) : (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        data-testid={`actions-provider-${provider.id}`}
                        aria-label={`Actions for ${provider.name}`}
                      >
                        <ForwardedIconComponent
                          name="EllipsisVertical"
                          className="h-4 w-4"
                        />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => onDeleteProvider?.(provider)}
                      >
                        <ForwardedIconComponent
                          name="Trash2"
                          className="mr-2 h-4 w-4"
                        />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </>
            </>
          );
        })}
      </>
    </>
  );
}
