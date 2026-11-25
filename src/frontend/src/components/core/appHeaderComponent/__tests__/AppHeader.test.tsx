import { render, screen } from "@testing-library/react";
import AppHeader from "../index";

jest.mock("@/alerts/alertDropDown", () => ({
  __esModule: true,
  default: ({ children }: any) => (
    <div data-testid="alert-dropdown">{children}</div>
  ),
}));
jest.mock("@/assets/FlowLogo.svg?react", () => ({
  __esModule: true,
  default: () => <svg data-testid="flow-logo" />,
}));
jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: any) => <span data-testid={`icon-${name}`}>{name}</span>,
}));
jest.mock("@/components/common/modelProviderCountComponent", () => ({
  __esModule: true,
  default: () => <div data-testid="model-provider-count" />,
}));
jest.mock("@/components/common/shadTooltipComponent", () => ({
  __esModule: true,
  default: ({ children }: any) => <div>{children}</div>,
}));
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, unstyled, ...rest }: any) => (
    <button {...rest}>{children}</button>
  ),
}));
jest.mock("@/customization/feature-flags", () => ({
  FLOW_AGENTIC_EXPERIENCE: false,
}));
jest.mock("@/customization/hooks/use-custom-navigate", () => ({
  useCustomNavigate: () => jest.fn(),
}));
jest.mock("@/customization/hooks/use-custom-theme", () => ({
  __esModule: true,
  default: () => ({}),
}));
jest.mock("@/stores/alertStore", () => ({
  __esModule: true,
  default: (sel: any) => sel({ notificationCenter: false }),
}));
jest.mock("../components/FlowMenu", () => ({
  __esModule: true,
  default: () => <div data-testid="flow-menu" />,
}));

describe("AppHeader standalone layout", () => {
  it("renders logo, FlowMenu, and notifications without GitHub/Discord counts or top-right AccountMenu", () => {
    render(<AppHeader />);

    expect(screen.getByTestId("app-header")).toBeInTheDocument();
    expect(screen.getByTestId("flow-logo")).toBeInTheDocument();
    expect(screen.getByTestId("flow-menu")).toBeInTheDocument();
    expect(screen.getByTestId("notification_button")).toBeInTheDocument();

    // No GitHub / Discord links or counters
    expect(screen.queryByText(/github/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/discord/i)).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("header-hanzo-app-link"),
    ).not.toBeInTheDocument();
    // No redundant top-right AccountMenu or top-left OrgSelector
    expect(
      screen.queryByTestId("user-profile-settings"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("hanzo-org-switcher")).not.toBeInTheDocument();
  });
});
