import { Building2, Check, ExternalLink } from "lucide-react";
import { useContext } from "react";
import { useTranslation } from "react-i18next";
import { AuthContext } from "@/contexts/authContext";
import { useLogout } from "@/controllers/API/queries/auth";
import { useSwitchIamOrg } from "@/controllers/API/queries/auth/use-get-iam-context";
import { CustomProfileIcon } from "@/customization/components/custom-profile-icon";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import useAuthStore from "@/stores/authStore";
import { useDarkStore } from "@/stores/darkStore";
import { useIamStore } from "@/stores/iamStore";
import {
  HeaderMenu,
  HeaderMenuItemButton,
  HeaderMenuItemLink,
  HeaderMenuItems,
  HeaderMenuToggle,
} from "../HeaderMenu";
import ThemeButtons from "../ThemeButtons";

export const AccountMenu = () => {
  const { t } = useTranslation();
  const version = useDarkStore((state) => state.version);
  const navigate = useCustomNavigate();
  const { mutate: mutationLogout } = useLogout();
  const { mutate: switchOrg } = useSwitchIamOrg();
  const { userData } = useContext(AuthContext);

  const autoLogin = useAuthStore((state) => state.autoLogin);
  const context = useIamStore((state) => state.context);

  const iamUser = context?.user;
  const activeOrg = context?.active_org ?? "";
  const activeOrgInfo = context?.active_org_info;
  const memberOrgs = (context?.orgs ?? []).filter((o) => o.is_member);
  const links = context?.links ?? {
    account: "https://hanzo.ai/account",
    billing: "https://hanzo.ai/account/billing",
    organizations: "https://hanzo.ai/account/organizations",
    app: "https://hanzo.app/flow",
    docs: "https://docs.hanzo.ai",
  };

  const displayName =
    iamUser?.display_name || iamUser?.username || userData?.username || "Account";
  const email = iamUser?.email || (userData?.username?.includes("@") ? userData.username : "");

  const handleLogout = () => {
    mutationLogout();
  };

  return (
    <HeaderMenu>
      <HeaderMenuToggle>
        <div
          className="h-6 w-6 rounded-full focus-visible:outline-0"
          data-testid="user-profile-settings"
        >
          <CustomProfileIcon />
        </div>
      </HeaderMenuToggle>
      <HeaderMenuItems position="right" classNameSize="w-[292px]">
        <div className="divide-y divide-foreground/10">
          {/* Identity header */}
          <div className="px-4 py-3" data-testid="account-menu-identity">
            <div className="flex items-center gap-2.5">
              <CustomProfileIcon className="h-9 w-9 text-xs" />
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
            {activeOrg && (
              <div className="mt-2.5 flex items-center justify-between rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs">
                <span className="flex min-w-0 items-center gap-1.5 text-foreground">
                  <Building2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate font-medium">
                    {activeOrgInfo?.display_name || activeOrg}
                  </span>
                </span>
                {activeOrgInfo?.plan && (
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {activeOrgInfo.plan}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Quick org switch for multi-org members */}
          {memberOrgs.length > 1 && (
            <div className="py-1" data-testid="account-menu-orgs">
              <div className="px-4 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Switch Organization
              </div>
              {memberOrgs.slice(0, 4).map((org) => {
                const isSelected = org.name === activeOrg;
                return (
                  <HeaderMenuItemButton
                    key={org.name}
                    onClick={() => {
                      if (!isSelected) {
                        switchOrg(org.name);
                      }
                    }}
                  >
                    <span className="flex w-full items-center justify-between gap-2 text-sm">
                      <span className="truncate">{org.display_name}</span>
                      {isSelected ? (
                        <Check className="h-3.5 w-3.5 shrink-0 text-foreground" />
                      ) : (
                        <span className="text-[11px] text-muted-foreground">
                          @{org.name}
                        </span>
                      )}
                    </span>
                  </HeaderMenuItemButton>
                );
              })}
            </div>
          )}

          {/* Flow Settings */}
          <div className="py-1">
            <HeaderMenuItemButton
              onClick={() => {
                navigate("/settings/general");
              }}
            >
              <span
                data-testid="menu_settings_button"
                id="menu_settings_button"
              >
                Account &amp; Organization
              </span>
            </HeaderMenuItemButton>
            <HeaderMenuItemButton
              onClick={() => {
                navigate("/settings/model-providers");
              }}
            >
              <span>Model Providers</span>
            </HeaderMenuItemButton>
            <HeaderMenuItemButton
              onClick={() => {
                navigate("/settings/mcp-servers");
              }}
            >
              <span>MCP Servers</span>
            </HeaderMenuItemButton>
          </div>

          {/* Hanzo Cloud / IAM Links */}
          <div className="py-1">
            <HeaderMenuItemLink newPage href={links.account} icon="">
              <span className="flex w-full items-center justify-between text-sm">
                <span>Hanzo Account</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
            </HeaderMenuItemLink>
            <HeaderMenuItemLink newPage href={links.billing} icon="">
              <span className="flex w-full items-center justify-between text-sm">
                <span>Billing &amp; Plan</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
            </HeaderMenuItemLink>
            <HeaderMenuItemLink newPage href={links.app} icon="">
              <span className="flex w-full items-center justify-between text-sm">
                <span>Open in Hanzo App</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
            </HeaderMenuItemLink>
            <HeaderMenuItemLink newPage href={links.docs} icon="">
              <span
                data-testid="menu_docs_button"
                id="menu_docs_button"
                className="flex w-full items-center justify-between text-sm"
              >
                <span>{t("account.docs")}</span>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
              </span>
            </HeaderMenuItemLink>
          </div>

          {/* Theme + Version */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 text-sm">
              <span>{t("account.theme")}</span>
              <div className="relative top-[1px]">
                <ThemeButtons />
              </div>
            </div>
            {version && (
              <div className="flex items-center justify-between px-4 pb-2 text-xs text-muted-foreground">
                <span data-testid="menu_version_button" id="menu_version_button">
                  Hanzo Flow
                </span>
                <span className="font-mono">v{version}</span>
              </div>
            )}
          </div>

          {/* Sign Out */}
          {!autoLogin && (
            <div className="py-1">
              <HeaderMenuItemButton onClick={handleLogout} icon="log-out">
                {t("account.logout")}
              </HeaderMenuItemButton>
            </div>
          )}
        </div>
      </HeaderMenuItems>
    </HeaderMenu>
  );
};
