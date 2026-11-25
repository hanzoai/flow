import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import McpClientPage from "../index";

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }: any) => <span data-testid={`icon-${name}`}>{name}</span>,
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, unstyled, ...rest }: any) => (
    <button {...rest}>{children}</button>
  ),
}));

jest.mock("@/customization/utils/custom-get-host-protocol", () => ({
  customGetHostProtocol: () => ({
    host: "flow.hanzo.ai",
    protocol: "https:",
  }),
}));

jest.mock("@/utils/utils", () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));

describe("McpClientPage", () => {
  it("removes Bob (IBM) and lfx-mcp and renders canonical Hanzo MCP client tabs with npx -y hanzo mcp", () => {
    render(
      <MemoryRouter>
        <McpClientPage />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/Bob \(IBM\)/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/lfx-mcp/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/uvx --from lfx/i)).not.toBeInTheDocument();

    expect(screen.getByTestId("mcp-client-tab-hanzo-dev")).toHaveTextContent(
      "Hanzo Dev / CLI",
    );
    expect(screen.getByTestId("mcp-client-tab-claude-code")).toHaveTextContent(
      "Claude Code",
    );
    expect(screen.getByTestId("mcp-client-tab-cursor")).toHaveTextContent(
      "Cursor",
    );

    const jsonBlock = screen.getByTestId("mcp-client-json-config");
    expect(jsonBlock.textContent).toContain('"command": "npx"');
    expect(jsonBlock.textContent).toContain('"-y"');
    expect(jsonBlock.textContent).toContain('"hanzo"');
    expect(jsonBlock.textContent).toContain('"mcp"');
    expect(jsonBlock.textContent).toContain("https://flow.hanzo.ai");

    // Switch to Claude Code tab and check CLI command uses npx -y hanzo mcp
    fireEvent.click(screen.getByTestId("mcp-client-tab-claude-code"));
    const cliBlock = screen.getByTestId("mcp-client-cli-command");
    expect(cliBlock.textContent).toContain(
      "claude mcp add hanzo -- npx -y hanzo mcp",
    );
    expect(cliBlock.textContent).not.toContain("lfx-mcp");

    // Switch to Cursor tab
    fireEvent.click(screen.getByTestId("mcp-client-tab-cursor"));
    expect(screen.getByText("~/.cursor/mcp.json")).toBeInTheDocument();
  });
});
