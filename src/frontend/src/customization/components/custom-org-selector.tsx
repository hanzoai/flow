import { Building2, Check, ChevronsUpDown, ExternalLink, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  useCreateIamOrg,
  useGetIamContext,
  useSwitchIamOrg,
} from "@/controllers/API/queries/auth/use-get-iam-context";
import useAuthStore from "@/stores/authStore";
import {
  getInitials,
  type IamOrgSummary,
  orgSlugPreview,
  useIamStore,
} from "@/stores/iamStore";
import { cn } from "@/utils/utils";

function OrgBadge({ org }: { org: IamOrgSummary }) {
  const [imgFailed, setImgFailed] = useState(false);
  const src = !imgFailed ? org.favicon || org.logo : "";

  if (src) {
    return (
      <img
        src={src}
        alt=""
        onError={() => setImgFailed(true)}
        className="h-5 w-5 shrink-0 rounded-sm border border-border object-cover bg-background"
      />
    );
  }

  return (
    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border border-border bg-muted text-[10px] font-semibold uppercase text-foreground">
      {getInitials(org.display_name || org.name)}
    </span>
  );
}

function formatRole(role: string, isPersonal: boolean): string {
  if (isPersonal) return "Personal";
  if (!role) return "";
  if (role === "superadmin") return "SuperAdmin";
  return role.charAt(0).toUpperCase() + role.slice(1);
}

export function CustomOrgSelector() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { isLoading } = useGetIamContext();
  const context = useIamStore((state) => state.context);
  const isSwitchingOrg = useIamStore((state) => state.isSwitchingOrg);

  const { mutate: switchOrg } = useSwitchIamOrg();
  const { mutate: createOrg, isPending: isCreating } = useCreateIamOrg();

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");

  const activeOrg = context?.active_org ?? "";
  const activeOrgInfo = context?.active_org_info ?? null;
  const orgs = context?.orgs ?? [];

  const { memberOrgs, otherOrgs } = useMemo(() => {
    const q = search.trim().toLowerCase();
    const match = (o: IamOrgSummary) =>
      !q ||
      o.display_name.toLowerCase().includes(q) ||
      o.name.toLowerCase().includes(q);

    const members = orgs.filter((o) => o.is_member && match(o));
    const others = orgs.filter((o) => {
      if (o.is_member) return false;
      // Hide synthetic wallet orgs from SuperAdmin list unless explicitly searched
      if (!q && o.name.startsWith("wallet-")) return false;
      return match(o);
    });
    return { memberOrgs: members, otherOrgs: others };
  }, [orgs, search]);

  if (!isAuthenticated) {
    return null;
  }

  const showSearch = orgs.length > 5;
  const activeLabel =
    activeOrgInfo?.display_name || activeOrg || (isLoading ? "..." : "Workspace");
  const activePlan = activeOrgInfo?.plan || "";
  const slug = orgSlugPreview(newOrgName);

  const handleSelect = (slugToSelect: string) => {
    setOpen(false);
    setSearch("");
    if (slugToSelect && slugToSelect !== activeOrg) {
      switchOrg(slugToSelect);
    }
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newOrgName.trim();
    if (trimmed.length < 2 || isCreating) return;
    createOrg(trimmed, {
      onSuccess: () => {
        setNewOrgName("");
        setCreateOpen(false);
      },
    });
  };

  return (
    <>
      <div className="flex items-center gap-1.5" data-testid="hanzo-org-switcher">
        <span className="select-none text-muted-foreground/40 text-sm">/</span>
        <DropdownMenu
          open={open}
          onOpenChange={(next) => {
            setOpen(next);
            if (!next) setSearch("");
          }}
        >
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={isSwitchingOrg}
              data-testid="org-switcher-trigger"
              className="flex h-8 max-w-[240px] items-center gap-2 rounded-md border border-transparent px-2 text-sm font-medium text-foreground hover:border-border hover:bg-muted/60"
            >
              {activeOrgInfo ? (
                <OrgBadge org={activeOrgInfo} />
              ) : (
                <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}
              <span className="truncate">{activeLabel}</span>
              {activePlan && (
                <span className="hidden rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium leading-none text-muted-foreground sm:inline-block">
                  {activePlan}
                </span>
              )}
              <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            align="start"
            className="w-[280px] p-1.5"
            data-testid="org-switcher-menu"
          >
            {showSearch && (
              <div className="relative px-1 pb-1.5 pt-0.5">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.stopPropagation()}
                  placeholder="Find organization..."
                  className="h-8 pl-8 text-xs"
                  data-testid="org-switcher-search"
                />
              </div>
            )}

            <DropdownMenuLabel className="px-2 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Organizations
            </DropdownMenuLabel>

            <div className="max-h-[260px] overflow-y-auto">
              {memberOrgs.map((org) => {
                const isSelected = org.name === activeOrg;
                return (
                  <DropdownMenuItem
                    key={org.name}
                    onSelect={() => handleSelect(org.name)}
                    data-testid={`org-option-${org.name}`}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm",
                      isSelected && "bg-muted/80 font-medium",
                    )}
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <OrgBadge org={org} />
                      <div className="flex min-w-0 flex-col">
                        <span className="truncate leading-tight">
                          {org.display_name}
                        </span>
                        <span className="truncate text-[11px] text-muted-foreground">
                          @{org.name}
                          {org.role ? ` · ${formatRole(org.role, org.is_personal)}` : ""}
                        </span>
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="h-4 w-4 shrink-0 text-foreground" />
                    )}
                  </DropdownMenuItem>
                );
              })}

              {otherOrgs.length > 0 && (
                <>
                  <DropdownMenuSeparator className="my-1" />
                  <DropdownMenuLabel className="px-2 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    All Organizations (SuperAdmin)
                  </DropdownMenuLabel>
                  {otherOrgs.slice(0, 40).map((org) => {
                    const isSelected = org.name === activeOrg;
                    return (
                      <DropdownMenuItem
                        key={org.name}
                        onSelect={() => handleSelect(org.name)}
                        data-testid={`org-option-${org.name}`}
                        className={cn(
                          "flex cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm",
                          isSelected && "bg-muted/80 font-medium",
                        )}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <OrgBadge org={org} />
                          <div className="flex min-w-0 flex-col">
                            <span className="truncate leading-tight">
                              {org.display_name}
                            </span>
                            <span className="truncate text-[11px] text-muted-foreground">
                              @{org.name}
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <Check className="h-4 w-4 shrink-0 text-foreground" />
                        )}
                      </DropdownMenuItem>
                    );
                  })}
                </>
              )}

              {memberOrgs.length === 0 && otherOrgs.length === 0 && (
                <div className="px-2 py-3 text-center text-xs text-muted-foreground">
                  No matching organizations.
                </div>
              )}
            </div>

            <DropdownMenuSeparator className="my-1" />

            <DropdownMenuItem
              onSelect={() => {
                setOpen(false);
                setCreateOpen(true);
              }}
              data-testid="org-switcher-create"
              className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm"
            >
              <Plus className="h-4 w-4 text-muted-foreground" />
              <span>Create organization</span>
            </DropdownMenuItem>

            <DropdownMenuItem asChild className="cursor-pointer rounded-md px-2 py-1.5 text-sm">
              <a
                href={
                  context?.links?.organizations ||
                  "https://hanzo.ai/account/organizations"
                }
                target="_blank"
                rel="noreferrer"
                className="flex w-full items-center justify-between"
              >
                <span className="text-muted-foreground">Manage in Hanzo IAM</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </a>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Create organization</DialogTitle>
            <DialogDescription>
              Creates a new Hanzo IAM organization you own and switches your Flow
              workspace into it.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="hanzo-new-org-name"
                className="text-sm font-medium text-foreground"
              >
                Organization name
              </label>
              <Input
                id="hanzo-new-org-name"
                autoFocus
                value={newOrgName}
                onChange={(e) => setNewOrgName(e.target.value)}
                placeholder="Acme Labs"
                maxLength={80}
                disabled={isCreating}
              />
              {slug && (
                <p className="text-xs text-muted-foreground">
                  Handle: <code className="font-mono text-foreground">@{slug}</code>
                </p>
              )}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={newOrgName.trim().length < 2 || isCreating}
              >
                {isCreating ? "Creating..." : "Create organization"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
