import { useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Check,
  ExternalLink,
  LogOut,
  Plus,
  Search,
  Settings,
  Shield,
} from "lucide-react";
import { useContext, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import ThemeButtons from "@/components/core/appHeaderComponent/components/ThemeButtons";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { DOCS_URL } from "@/constants/constants";
import { AuthContext } from "@/contexts/authContext";
import { useLogout } from "@/controllers/API/queries/auth";
import {
  useCreateIamOrg,
  useGetIamContext,
  useSwitchIamOrg,
} from "@/controllers/API/queries/auth/use-get-iam-context";
import { CustomProfileIcon } from "@/customization/components/custom-profile-icon";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import useAuthStore from "@/stores/authStore";
import { useDarkStore } from "@/stores/darkStore";
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

function readFallbackOrg(): string | null {
  try {
    return (
      window.localStorage.getItem("hanzo_active_org") ||
      window.localStorage.getItem("hanzo_flow_active_org")
    );
  } catch {
    return null;
  }
}

export interface BottomSettingsMenuProps {
  variant?: "rail" | "sidebar";
  className?: string;
}

export function BottomSettingsMenu({
  variant = "rail",
  className,
}: BottomSettingsMenuProps) {
  const { t } = useTranslation();
  const navigate = useCustomNavigate();
  const queryClient = useQueryClient();
  const version = useDarkStore((state) => state.version);
  const { userData: authContextUser } = useContext(AuthContext);
  const storeUserData = useAuthStore((state) => state.userData);
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const autoLogin = useAuthStore((state) => state.autoLogin);

  const userData = storeUserData ?? authContextUser;

  useGetIamContext();
  const context = useIamStore((state) => state.context);
  const storeActiveOrg = useIamStore((state) => state.activeOrg);
  const setActiveOrg = useIamStore((state) => state.setActiveOrg);
  const isSwitchingOrg = useIamStore((state) => state.isSwitchingOrg);

  const { mutate: switchIamOrg } = useSwitchIamOrg();
  const { mutate: createOrg, isPending: isCreating } = useCreateIamOrg();
  const { mutate: mutationLogout } = useLogout();

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");

  const iamUser = context?.user;
  const activeOrg =
    context?.active_org ||
    storeActiveOrg ||
    readFallbackOrg() ||
    userData?.org_id ||
    userData?.optins?.org ||
    "hanzo";
  const activeOrgInfo = context?.active_org_info ?? null;

  const orgs: IamOrgSummary[] = useMemo(() => {
    if (context?.orgs && context.orgs.length > 0) {
      return context.orgs;
    }
    return [
      {
        name: activeOrg,
        display_name: activeOrgInfo?.display_name || activeOrg,
        role: activeOrgInfo?.role || "",
        is_personal: activeOrgInfo?.is_personal ?? false,
        is_member: true,
        logo: activeOrgInfo?.logo || "",
        favicon: activeOrgInfo?.favicon || "",
        website_url: activeOrgInfo?.website_url || "",
        plan: activeOrgInfo?.plan || "",
      },
    ];
  }, [context?.orgs, activeOrg, activeOrgInfo]);

  const { memberOrgs, otherOrgs } = useMemo(() => {
    const q = search.trim().toLowerCase();
    const match = (o: IamOrgSummary) =>
      !q ||
      o.display_name.toLowerCase().includes(q) ||
      o.name.toLowerCase().includes(q);

    const members = orgs.filter((o) => o.is_member && match(o));
    const others = orgs.filter((o) => {
      if (o.is_member) return false;
      if (!q && o.name.startsWith("wallet-")) return false;
      return match(o);
    });
    return { memberOrgs: members, otherOrgs: others };
  }, [orgs, search]);

  const displayName =
    iamUser?.display_name ||
    iamUser?.username ||
    userData?.username ||
    "Account";
  const email =
    iamUser?.email ||
    (userData?.username?.includes("@") ? userData.username : "");
  const docsUrl = context?.links?.docs || DOCS_URL;
  const orgsUrl =
    context?.links?.organizations || "https://hanzo.ai/account/organizations";
  const showSearch = orgs.length > 5;
  const slug = orgSlugPreview(newOrgName);

  const handleSelectOrg = (slugToSelect: string) => {
    setOpen(false);
    setSearch("");
    if (!slugToSelect || slugToSelect === activeOrg) {
      return;
    }
    if (context?.iam_enabled) {
      switchIamOrg(slugToSelect);
    } else {
      setActiveOrg(slugToSelect);
      queryClient.invalidateQueries();
    }
  };

  const handleNavigate = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  const handleLogout = () => {
    setOpen(false);
    mutationLogout();
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

  const triggerButton =
    variant === "sidebar" ? (
      <button
        type="button"
        data-testid="bottom-settings-cog"
        aria-label="Settings & Organization"
        className={cn(
          "flex h-9 w-full items-center justify-between gap-2 rounded-md px-2 text-sm text-secondary-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          open && "bg-accent text-accent-foreground",
          className,
        )}
      >
        <span className="flex min-w-0 items-center gap-2">
          <Settings className="h-4 w-4 shrink-0" />
          <span className="truncate font-medium">Settings</span>
        </span>
        <span
          className="max-w-[120px] truncate rounded border border-border bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground"
          data-testid="bottom-settings-active-org"
        >
          {activeOrgInfo?.display_name || activeOrg}
        </span>
      </button>
    ) : (
      <button
        type="button"
        data-testid="bottom-settings-cog"
        aria-label="Settings & Organization"
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-md p-0 transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          open
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          className,
        )}
      >
        <Settings className="h-5 w-5" />
        <span className="sr-only">Settings &amp; Organization</span>
      </button>
    );

  return (
    <>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setSearch("");
        }}
      >
        <ShadTooltip content="Settings & Organization" side="right">
          <PopoverTrigger asChild>{triggerButton}</PopoverTrigger>
        </ShadTooltip>

        <PopoverContent
          side="right"
          align="end"
          sideOffset={8}
          className="w-[292px] p-0"
          data-testid="bottom-settings-popover"
        >
          <div className="divide-y divide-border">
            {/* User Identity */}
            <div className="px-3.5 py-3" data-testid="account-menu-identity">
              <div className="flex items-center gap-2.5">
                <CustomProfileIcon className="h-8 w-8 text-xs" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-semibold text-foreground">
                      {displayName}
                    </span>
                    {iamUser?.is_super_admin && (
                      <span className="shrink-0 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium leading-none text-foreground">
                        SuperAdmin
                      </span>
                    )}
                  </div>
                  {email && (
                    <p className="truncate text-xs text-muted-foreground">
                      {email}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-2.5 flex items-center justify-between rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs">
                <span className="flex min-w-0 items-center gap-1.5 text-foreground">
                  <Building2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span
                    className="truncate font-medium"
                    data-testid="bottom-settings-org-badge"
                  >
                    {activeOrgInfo?.display_name || activeOrg}
                  </span>
                </span>
                {activeOrgInfo?.plan && (
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {activeOrgInfo.plan}
                  </span>
                )}
              </div>
            </div>

            {/* Organization Switcher */}
            <div className="p-2" data-testid="org-switcher-section">
              <div className="px-1.5 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Organization
              </div>

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

              <div className="max-h-[180px] space-y-0.5 overflow-y-auto">
                {memberOrgs.map((org) => {
                  const isSelected = org.name === activeOrg;
                  return (
                    <button
                      key={org.name}
                      type="button"
                      disabled={isSwitchingOrg}
                      onClick={() => handleSelectOrg(org.name)}
                      data-testid={`org-option-${org.name}`}
                      className={cn(
                        "flex w-full cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                        isSelected && "bg-muted font-medium",
                      )}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <OrgBadge org={org} />
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate leading-tight text-foreground">
                            {org.display_name}
                          </span>
                          <span className="truncate text-[11px] text-muted-foreground">
                            @{org.name}
                            {org.role
                              ? ` · ${formatRole(org.role, org.is_personal)}`
                              : ""}
                          </span>
                        </div>
                      </div>
                      {isSelected && (
                        <Check className="h-4 w-4 shrink-0 text-foreground" />
                      )}
                    </button>
                  );
                })}

                {otherOrgs.length > 0 && (
                  <>
                    <div className="px-1.5 pt-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      All Organizations (SuperAdmin)
                    </div>
                    {otherOrgs.slice(0, 30).map((org) => {
                      const isSelected = org.name === activeOrg;
                      return (
                        <button
                          key={org.name}
                          type="button"
                          disabled={isSwitchingOrg}
                          onClick={() => handleSelectOrg(org.name)}
                          data-testid={`org-option-${org.name}`}
                          className={cn(
                            "flex w-full cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
                            isSelected && "bg-muted font-medium",
                          )}
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <OrgBadge org={org} />
                            <div className="flex min-w-0 flex-col">
                              <span className="truncate leading-tight text-foreground">
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
                        </button>
                      );
                    })}
                  </>
                )}

                {memberOrgs.length === 0 && otherOrgs.length === 0 && (
                  <div className="px-2 py-2 text-center text-xs text-muted-foreground">
                    No matching organizations.
                  </div>
                )}
              </div>

              {context?.iam_enabled && (
                <div className="mt-1.5 flex items-center justify-between gap-1 border-t border-border pt-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      setCreateOpen(true);
                    }}
                    data-testid="org-switcher-create"
                    className="flex flex-1 cursor-pointer items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Create org</span>
                  </button>
                  <a
                    href={orgsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    <span>Manage</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="p-1.5">
              <button
                type="button"
                onClick={() => handleNavigate("/settings")}
                data-testid="menu_settings_button"
                id="menu_settings_button"
                className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <span>{t("account.settings")}</span>
              </button>

              {isAdmin && !autoLogin && (
                <button
                  type="button"
                  onClick={() => handleNavigate("/admin")}
                  data-testid="menu_admin_button"
                  id="menu_admin_button"
                  className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  <span>{t("account.adminPage")}</span>
                  <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              )}

              <a
                href={docsUrl}
                target="_blank"
                rel="noreferrer"
                data-testid="menu_docs_button"
                id="menu_docs_button"
                className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <span>{t("account.docs")}</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </a>
            </div>

            {/* Theme & Version */}
            <div className="px-3.5 py-2.5 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-foreground">{t("account.theme")}</span>
                <ThemeButtons />
              </div>
              {version && (
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span
                    data-testid="menu_version_button"
                    id="menu_version_button"
                  >
                    Hanzo Flow
                  </span>
                  <span className="font-mono">v{version}</span>
                </div>
              )}
            </div>

            {/* Sign Out */}
            {!autoLogin && (
              <div className="p-1.5">
                <button
                  type="button"
                  onClick={handleLogout}
                  data-testid="menu_logout_button"
                  className="flex w-full cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  <span>{t("account.logout")}</span>
                  <LogOut className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              </div>
            )}
          </div>
        </PopoverContent>
      </Popover>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Create organization</DialogTitle>
            <DialogDescription>
              Creates a new Hanzo IAM organization you own and switches your
              Flow workspace into it.
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
                  Handle:{" "}
                  <code className="font-mono text-foreground">@{slug}</code>
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

export default BottomSettingsMenu;
