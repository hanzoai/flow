import { Outlet, type To } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SideBarButtonsComponent from "@/components/core/sidebarComponent";
import { SidebarProvider } from "@/components/ui/sidebar";
import { CustomStoreSidebar } from "@/customization/components/custom-store-sidebar";
import { ENABLE_DATASTAX_FLOW } from "@/customization/feature-flags";
import ForwardedIconComponent from "../../components/common/genericIconComponent";
import PageLayout from "../../components/common/pageLayout";

export default function SettingsPage(): JSX.Element {
  const { t } = useTranslation();

  const sidebarNavItems: {
    href?: string;
    title: string;
    icon: React.ReactNode;
  }[] = [
    {
      title: "Account & Organization",
      href: "/settings/general",
      icon: (
        <ForwardedIconComponent
          name="Building2"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.nav.modelProviders"),
      href: "/settings/model-providers",
      icon: (
        <ForwardedIconComponent
          name="Brain"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.nav.globalVariables"),
      href: "/settings/global-variables",
      icon: (
        <ForwardedIconComponent
          name="Globe"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.nav.mcpServers"),
      href: "/settings/mcp-servers",
      icon: (
        <ForwardedIconComponent
          name="Mcp"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: "Flow MCP Client",
      href: "/settings/mcp-client",
      icon: (
        <ForwardedIconComponent
          name="Terminal"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.nav.shortcuts"),
      href: "/settings/shortcuts",
      icon: (
        <ForwardedIconComponent
          name="Keyboard"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.nav.messages"),
      href: "/settings/messages",
      icon: (
        <ForwardedIconComponent
          name="MessagesSquare"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
  ];

  if (!ENABLE_DATASTAX_FLOW) {
    const flowItems = CustomStoreSidebar(true, false);
    sidebarNavItems.splice(5, 0, ...flowItems);
  }

  return (
    <PageLayout
      backTo={-1 as To}
      title="Settings"
      description="Manage your Hanzo account, organizations, model providers, and Flow settings."
    >
      <SidebarProvider width="15rem" defaultOpen={false}>
        <SideBarButtonsComponent items={sidebarNavItems} />
        <main className="flex flex-1 overflow-hidden">
          <div className="flex flex-1 flex-col overflow-x-hidden pt-1">
            <Outlet />
          </div>
        </main>
      </SidebarProvider>
    </PageLayout>
  );
}
