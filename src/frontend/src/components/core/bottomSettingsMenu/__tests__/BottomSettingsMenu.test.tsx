import { fireEvent, render, screen } from "@testing-library/react";
import { AuthContext } from "@/contexts/authContext";
import type { IamContext } from "@/stores/iamStore";
import BottomSettingsMenu from "../index";

const mockNavigate = jest.fn();
const mockInvalidateQueries = jest.fn();
const mockSwitchIamOrg = jest.fn();
const mockCreateOrg = jest.fn();
const mockLogout = jest.fn();
const mockSetActiveOrg = jest.fn();

let mockIamContext: IamContext | null = null;
let mockActiveOrg: string | null = "hanzo";
let mockIsAdmin = false;
let mockAutoLogin = false;

jest.mock("@tanstack/react-query", () => ({
  ...jest.requireActual("@tanstack/react-query"),
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
}));

jest.mock("@/contexts/authContext", () => {
  const React = require("react");
  return {
    AuthContext: React.createContext({ userData: null }),
  };
});

jest.mock("@/customization/hooks/use-custom-navigate", () => ({
  useCustomNavigate: () => mockNavigate,
}));

jest.mock("@/controllers/API/queries/auth", () => ({
  useLogout: () => ({ mutate: mockLogout }),
}));

jest.mock("@/controllers/API/queries/auth/use-get-iam-context", () => ({
  useGetIamContext: () => ({ isLoading: false }),
  useSwitchIamOrg: () => ({ mutate: mockSwitchIamOrg }),
  useCreateIamOrg: () => ({ mutate: mockCreateOrg, isPending: false }),
}));

jest.mock("@/stores/authStore", () => ({
  __esModule: true,
  default: (sel: any) =>
    sel({
      userData: {
        id: "u1",
        username: "zach@hanzo.ai",
        org_id: "hanzo",
      },
      isAdmin: mockIsAdmin,
      autoLogin: mockAutoLogin,
    }),
}));

jest.mock("@/stores/darkStore", () => ({
  useDarkStore: (sel: any) => sel({ version: "1.8.16" }),
}));

jest.mock("@/stores/iamStore", () => ({
  getInitials: (name?: string) => (name ? name.slice(0, 2).toUpperCase() : "?"),
  orgSlugPreview: (name: string) => name.toLowerCase().replace(/\s+/g, "-"),
  useIamStore: (sel: any) =>
    sel({
      context: mockIamContext,
      activeOrg: mockActiveOrg,
      setActiveOrg: mockSetActiveOrg,
      isSwitchingOrg: false,
    }),
}));

jest.mock("@/customization/components/custom-profile-icon", () => ({
  CustomProfileIcon: () => <span data-testid="profile-icon">ZK</span>,
}));

jest.mock(
  "@/components/core/appHeaderComponent/components/ThemeButtons",
  () => ({
    __esModule: true,
    default: () => <div data-testid="theme-buttons">ThemeButtons</div>,
  }),
);

jest.mock("@/components/common/shadTooltipComponent", () => ({
  __esModule: true,
  default: ({ children, content }: any) => (
    <div data-testid="tooltip" data-content={content}>
      {children}
    </div>
  ),
}));

jest.mock("@/components/ui/popover", () => ({
  Popover: ({ children, open }: any) => (
    <div data-testid="popover-root" data-open={open}>
      {children}
    </div>
  ),
  PopoverTrigger: ({ children }: any) => <>{children}</>,
  PopoverContent: ({ children, ...rest }: any) => (
    <div {...rest}>{children}</div>
  ),
}));

jest.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogDescription: ({ children }: any) => <p>{children}</p>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h3>{children}</h3>,
}));

jest.mock("@/utils/utils", () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));

function renderMenu(variant: "rail" | "sidebar" = "rail") {
  return render(
    <AuthContext.Provider value={{ userData: null } as any}>
      <BottomSettingsMenu variant={variant} />
    </AuthContext.Provider>,
  );
}

describe("BottomSettingsMenu", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    mockIsAdmin = false;
    mockAutoLogin = false;
    mockActiveOrg = "hanzo";
    mockIamContext = {
      iam_enabled: true,
      issuer: "https://hanzo.id",
      user: {
        id: "u1",
        sub: "sub-1",
        did: "did:hanzo:u1",
        username: "zach",
        display_name: "Zach Kelling",
        email: "zach@hanzo.ai",
        picture: "",
        owner: "hanzo",
        is_super_admin: true,
      },
      active_org: "hanzo",
      active_org_info: {
        name: "hanzo",
        display_name: "Hanzo AI",
        role: "owner",
        is_personal: false,
        is_member: true,
        logo: "",
        favicon: "",
        website_url: "",
        plan: "Enterprise",
      },
      orgs: [
        {
          name: "hanzo",
          display_name: "Hanzo AI",
          role: "owner",
          is_personal: false,
          is_member: true,
          logo: "",
          favicon: "",
          website_url: "",
          plan: "Enterprise",
        },
        {
          name: "lux",
          display_name: "Lux Network",
          role: "admin",
          is_personal: false,
          is_member: true,
          logo: "",
          favicon: "",
          website_url: "",
          plan: "Pro",
        },
      ],
      links: {
        account: "https://hanzo.ai/account",
        billing: "https://hanzo.ai/account/billing",
        organizations: "https://hanzo.ai/account/organizations",
        app: "https://hanzo.app/flow",
        docs: "https://docs.hanzo.ai/flow",
      },
    };
  });

  it("renders bottom-left Settings cog with tooltip and zero GitHub/Discord/Twitter links", () => {
    renderMenu("rail");

    expect(screen.getByTestId("bottom-settings-cog")).toBeInTheDocument();
    expect(screen.getByTestId("tooltip")).toHaveAttribute(
      "data-content",
      "Settings & Organization",
    );
    expect(screen.getByText("Zach Kelling")).toBeInTheDocument();
    expect(screen.getByText("zach@hanzo.ai")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-settings-org-badge")).toHaveTextContent(
      "Hanzo AI",
    );
    expect(screen.getByTestId("theme-buttons")).toBeInTheDocument();
    expect(screen.getByTestId("menu_settings_button")).toBeInTheDocument();
    expect(screen.getByTestId("menu_docs_button")).toBeInTheDocument();
    expect(screen.getByTestId("menu_logout_button")).toBeInTheDocument();

    // Verify zero GitHub / Discord / Twitter links
    const links = screen.queryAllByRole("link");
    links.forEach((link) => {
      const href = link.getAttribute("href") || "";
      expect(href).not.toMatch(/github\.com|discord\.com|x\.com|twitter\.com/i);
    });
    expect(screen.queryByText(/github/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/discord/i)).not.toBeInTheDocument();
  });

  it("switches organization via IAM mutation when iam_enabled is true", () => {
    renderMenu("sidebar");

    fireEvent.click(screen.getByTestId("org-option-lux"));
    expect(mockSwitchIamOrg).toHaveBeenCalledWith("lux");
  });

  it("falls back to local org switching and invalidates queries when IAM is unavailable", () => {
    mockIamContext = {
      ...mockIamContext!,
      iam_enabled: false,
    };
    renderMenu("rail");

    fireEvent.click(screen.getByTestId("org-option-lux"));
    expect(mockSetActiveOrg).toHaveBeenCalledWith("lux");
    expect(mockInvalidateQueries).toHaveBeenCalled();
  });

  it("navigates to /settings, /admin (when admin), and signs out", () => {
    mockIsAdmin = true;
    renderMenu("rail");

    fireEvent.click(screen.getByTestId("menu_settings_button"));
    expect(mockNavigate).toHaveBeenCalledWith("/settings");

    fireEvent.click(screen.getByTestId("menu_admin_button"));
    expect(mockNavigate).toHaveBeenCalledWith("/admin");

    fireEvent.click(screen.getByTestId("menu_logout_button"));
    expect(mockLogout).toHaveBeenCalled();
  });
});
