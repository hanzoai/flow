import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@hanzo/ui";
import { useDeleteProviderAccount } from "@/controllers/API/queries/deployment-provider-accounts/use-delete-provider-account";
import DeleteConfirmationModal from "@/modals/deleteConfirmationModal";
import { useDeleteWithConfirmation } from "../hooks/use-delete-with-confirmation";
import type { ProviderAccount } from "../types";
import AddProviderModal from "./add-provider-modal";
import ProvidersTable from "./providers-table";

const buildProviderDeleteParams = (id: string) => ({ provider_id: id });

interface ProvidersContentProps {
  isLoading: boolean;
  providers: ProviderAccount[];
  addProviderOpen: boolean;
  setAddProviderOpen: (open: boolean) => void;
}

function ProvidersLoadingSkeleton() {
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
        {Array.from({ length: 3 }).map((_, i) => (
          <>
            <>
              
            </>
            <>
              
            </>
            <>
              
            </>
            <>
              
            </>
            <>
              
            </>
          </>
        ))}
      </>
    </>
  );
}

function ProvidersEmptyState({ onAddProvider }: { onAddProvider: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <h3 className="text-lg font-semibold">No Environments</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Add your first environment to start deploying your flows.
      </p>
      <Button
        variant="outline"
        className="mt-4"
        data-testid="add-provider-empty-btn"
        onClick={onAddProvider}
      >
        <ForwardedIconComponent name="Plus" className="h-4 w-4" />
        Add Environment
      </Button>
    </div>
  );
}

export default function ProvidersContent({
  isLoading,
  providers,
  addProviderOpen,
  setAddProviderOpen,
}: ProvidersContentProps) {
  const { mutate: deleteProviderAccount } = useDeleteProviderAccount();

  const providerDelete = useDeleteWithConfirmation(
    deleteProviderAccount,
    buildProviderDeleteParams,
    "Error deleting environment",
  );

  const content = (() => {
    if (isLoading) return <ProvidersLoadingSkeleton />;
    if (providers.length === 0)
      return (
        <ProvidersEmptyState onAddProvider={() => setAddProviderOpen(true)} />
      );
    return (
      <ProvidersTable
        providers={providers}
        deletingId={providerDelete.deletingId}
        onDeleteProvider={providerDelete.requestDelete}
      />
    );
  })();

  return (
    <>
      {content}

      <AddProviderModal open={addProviderOpen} setOpen={setAddProviderOpen} />

      <DeleteConfirmationModal
        open={!!providerDelete.target}
        setOpen={providerDelete.setModalOpen}
        description={`environment "${providerDelete.target?.name}"`}
        onConfirm={providerDelete.confirmDelete}
      />
    </>
  );
}
