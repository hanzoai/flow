import {
  Building2,
  Check,
  Copy,
  ExternalLink,
  LogOut,
  Plus,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useContext, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import ThemeButtons from "@/components/core/appHeaderComponent/components/ThemeButtons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogout } from "@/controllers/API/queries/auth";
import {
  useCreateIamOrg,
  useGetIamContext,
  useSwitchIamOrg,
} from "@/controllers/API/queries/auth/use-get-iam-context";
import { CustomProfileIcon } from "@/customization/components/custom-profile-icon";
import { CustomTermsLinks } from "@/customization/components/custom-terms-links";
import useAlertStore from "@/stores/alertStore";
import {
  getInitials,
  type IamOrgSummary,
  orgSlugPreview,
  useIamStore,
} from "@/stores/iamStore";
import { AuthContext } from "../../../../contexts/authContext";
import useScrollToElement from "../hooks/use-scroll-to-element";
import GeneralPageHeaderComponent from "./components/GeneralPageHeader";

function OrgRowMark({ org }: { org: IamOrgSummary }) {
  const [failed, setFailed] = useState(false);
  const src = !failed ? org.favicon || org.logo : "";
  if (src) {
    return (
      <img
        src={src}
        alt=""
        onError={() => setFailed(true)}
        className="h-8 w-8 shrink-0 rounded-md border border-border object-cover bg-background"
      />
    );
  }
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-xs font-semibold uppercase text-foreground">
      {getInitials(org.display_name || org.name)}
    </span>
  );
}

export const GeneralPage = () => {
  const { scrollId } = useParams();
  useScrollToElement(scrollId);

  const { userData } = useContext(AuthContext);
  const { isLoading } = useGetIamContext();
  const context = useIamStore((state) => state.context);
  const isSwitchingOrg = useIamStore((state) => state.isSwitchingOrg);

  const { mutate: switchOrg } = useSwitchIamOrg();
  const { mutate: createOrg, isPending: isCreating } = useCreateIamOrg();
  const { mutate: mutationLogout } = useLogout();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);

  const [orgSearch, setOrgSearch] = useState("");
  const [newOrgName, setNewOrgName] = useState("");
  const [copiedId, setCopiedId] = useState(false);

  const iamUser = context?.user;
  const activeOrg = context?.active_org ?? "";
  const activeOrgInfo = context?.active_org_info ?? null;
  const allOrgs = context?.orgs ?? [];
  const links = context?.links ?? {
    account: "https://hanzo.ai/account",
    billing: "https://hanzo.ai/account/billing",
    organizations: "https://hanzo.ai/account/organizations",
    app: "https://hanzo.app/flow",
    docs: "https://docs.hanzo.ai",
  };

  const filteredOrgs = useMemo(() => {
    const q = orgSearch.trim().toLowerCase();
    return allOrgs.filter((org) => {
      if (!q && !org.is_member && org.name.startsWith("wallet-")) return false;
      if (!q) return true;
      return (
        org.display_name.toLowerCase().includes(q) ||
        org.name.toLowerCase().includes(q)
      );
    });
  }, [allOrgs, orgSearch]);

  const displayName =
    iamUser?.display_name ||
    iamUser?.username ||
    userData?.username ||
    "Hanzo User";
  const email =
    iamUser?.email ||
    (userData?.username?.includes("@") ? userData.username : "");
  const identityId = iamUser?.did || iamUser?.sub || userData?.id || "";
  const previewSlug = orgSlugPreview(newOrgName);

  const handleCopyIdentity = async () => {
    if (!identityId) return;
    try {
      await navigator.clipboard.writeText(identityId);
      setCopiedId(true);
      setSuccessData({ title: "Copied Hanzo identity ID" });
      setTimeout(() => setCopiedId(false), 1800);
    } catch {
      // Ignore clipboard permission errors
    }
  };

  const handleCreateOrg = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newOrgName.trim();
    if (trimmed.length < 2 || isCreating) return;
    createOrg(trimmed, {
      onSuccess: () => {
        setNewOrgName("");
      },
    });
  };

  return (
    <div className="flex h-full w-full flex-col gap-6 overflow-x-hidden pb-8">
      <GeneralPageHeaderComponent />

      <div className="flex w-full flex-col gap-6">
        {/* 1. Hanzo IAM Identity Card */}
        <Card data-testid="settings-iam-account-card">
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-base">Hanzo Account</CardTitle>
              <CardDescription>
                Single sign-on identity shared across Hanzo Flow, Hanzo App, and
                Hanzo Cloud.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <a href={links.account} target="_blank" rel="noreferrer">
                <span>Manage on hanzo.ai</span>
                <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
              </a>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-4">
              <CustomProfileIcon className="h-12 w-12 text-base" />
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-base font-semibold text-foreground">
                    {displayName}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    <ShieldCheck className="h-3 w-3 text-foreground" />
                    Hanzo IAM
                  </span>
                  {iamUser?.is_super_admin && (
                    <span className="rounded-md border border-border bg-foreground px-2 py-0.5 text-xs font-medium text-background">
                      SuperAdmin
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                  {email && <span>{email}</span>}
                  {iamUser?.username && (
                    <span className="font-mono text-xs">@{iamUser.username}</span>
                  )}
                </div>
              </div>
            </div>

            {identityId && (
              <div className="flex items-center justify-between gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs">
                <div className="min-w-0">
                  <span className="mr-2 text-muted-foreground">
                    {iamUser?.did ? "DID" : "Subject"}
                  </span>
                  <code className="truncate font-mono text-foreground">
                    {identityId}
                  </code>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={handleCopyIdentity}
                >
                  {copiedId ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2. Active Organization & Switcher Card */}
        <Card data-testid="settings-iam-organizations-card">
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-base">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span>Organizations</span>
              </CardTitle>
              <CardDescription>
                Flows, projects, and AI billing are scoped to your active Hanzo
                organization.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" asChild>
                <a href={links.billing} target="_blank" rel="noreferrer">
                  <span>Billing &amp; Plan</span>
                  <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                </a>
              </Button>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            {activeOrg && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 p-3.5">
                <div className="flex items-center gap-3">
                  {activeOrgInfo && <OrgRowMark org={activeOrgInfo} />}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">
                        {activeOrgInfo?.display_name || activeOrg}
                      </span>
                      <span className="rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-medium text-foreground">
                        Active
                      </span>
                      {activeOrgInfo?.plan && (
                        <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                          {activeOrgInfo.plan}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      @{activeOrg}
                      {activeOrgInfo?.role
                        ? ` · ${activeOrgInfo.role}`
                        : ""}
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm" asChild>
                  <a href={links.organizations} target="_blank" rel="noreferrer">
                    <span>Members &amp; Roles</span>
                    <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                  </a>
                </Button>
              </div>
            )}

            {allOrgs.length > 5 && (
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  value={orgSearch}
                  onChange={(e) => setOrgSearch(e.target.value)}
                  placeholder="Filter organizations by name or handle..."
                  className="pl-9"
                />
              </div>
            )}

            <div className="divide-y divide-border rounded-lg border border-border">
              {isLoading && allOrgs.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">
                  Loading Hanzo organizations...
                </div>
              ) : filteredOrgs.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">
                  No matching organizations.
                </div>
              ) : (
                filteredOrgs.slice(0, 30).map((org) => {
                  const isActive = org.name === activeOrg;
                  return (
                    <div
                      key={org.name}
                      className="flex items-center justify-between gap-3 px-3.5 py-2.5"
                      data-testid={`settings-org-row-${org.name}`}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <OrgRowMark org={org} />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm font-medium text-foreground">
                              {org.display_name}
                            </span>
                            {org.is_personal && (
                              <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                Personal
                              </span>
                            )}
                            {!org.is_member && (
                              <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                SuperAdmin
                              </span>
                            )}
                          </div>
                          <p className="truncate text-xs text-muted-foreground">
                            @{org.name}
                            {org.role ? ` · ${org.role}` : ""}
                          </p>
                        </div>
                      </div>
                      {isActive ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-foreground">
                          <Check className="h-3.5 w-3.5" />
                          Active
                        </span>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={isSwitchingOrg}
                          onClick={() => switchOrg(org.name)}
                        >
                          Switch
                        </Button>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Create new organization */}
            <form
              onSubmit={handleCreateOrg}
              className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-3.5 sm:flex-row sm:items-end"
            >
              <div className="flex-1 space-y-1">
                <label
                  htmlFor="settings-create-org"
                  className="text-xs font-medium text-foreground"
                >
                  Create a new Hanzo organization
                </label>
                <Input
                  id="settings-create-org"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="Organization name (e.g. Acme Labs)"
                  maxLength={80}
                  disabled={isCreating}
                />
                {previewSlug && (
                  <p className="text-[11px] text-muted-foreground">
                    Handle: <code className="font-mono">@{previewSlug}</code>
                  </p>
                )}
              </div>
              <Button
                type="submit"
                size="sm"
                disabled={newOrgName.trim().length < 2 || isCreating}
                className="sm:mb-0.5"
              >
                <Plus className="mr-1.5 h-4 w-4" />
                {isCreating ? "Creating..." : "Create"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* 3. Preferences & Session */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Workspace &amp; Session</CardTitle>
            <CardDescription>
              Appearance preferences and active session controls.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-foreground">Theme</p>
                <p className="text-xs text-muted-foreground">
                  Choose light, dark, or match your system theme.
                </p>
              </div>
              <ThemeButtons />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
              <Button variant="outline" size="sm" asChild>
                <a href={links.app} target="_blank" rel="noreferrer">
                  <span>Open Flow in Hanzo App</span>
                  <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                </a>
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => mutationLogout()}
                data-testid="settings-signout-button"
              >
                <LogOut className="mr-1.5 h-4 w-4" />
                Sign out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <CustomTermsLinks />
    </div>
  );
};

export default GeneralPage;
