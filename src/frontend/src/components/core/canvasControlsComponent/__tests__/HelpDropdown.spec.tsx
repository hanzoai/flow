import { fireEvent, render, screen } from "@testing-library/react";
import { HelpDropdownView } from "../HelpDropdownView";




jest.mock("../DropdownControlButton", () => ({
  __esModule: true,
  default: ({ label, onClick, disabled, testId }) => (
    <button
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
    >
      {label}
    </button>
  ),
}));

jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  default: ({ name }) => <span data-testid="icon">{name}</span>,
}));

// Minimize utils import surface (prevents pulling heavy modules)
jest.mock("@/utils/utils", () => ({
  __esModule: true,
  getOS: () => "macos",
  cn: (...args: Array<string>) => args.filter(Boolean).join(" "),
}));

describe("HelpDropdownView", () => {
  it("calls provided handlers for each menu item", () => {
    const onOpenChange = jest.fn();
    const onToggleHelperLines = jest.fn();
    const navigateTo = jest.fn();
    const openLink = jest.fn();
    const urls = {
      docs: "https://docs",
      bugReport: "https://bugs",
      desktop: "https://desktop",
    };

    render(
      <HelpDropdownView
        isOpen={true}
        onOpenChange={onOpenChange}
        helperLineEnabled={false}
        onToggleHelperLines={onToggleHelperLines}
        navigateTo={navigateTo}
        openLink={openLink}
        urls={urls}
      />,
    );

    fireEvent.click(screen.getByTestId("canvas_controls_dropdown_docs"));
    expect(openLink).toHaveBeenCalledWith("https://docs");

    fireEvent.click(screen.getByTestId("canvas_controls_dropdown_shortcuts"));
    expect(navigateTo).toHaveBeenCalledWith("/settings/shortcuts");

    fireEvent.click(
      screen.getByTestId("canvas_controls_dropdown_report_a_bug"),
    );
    expect(openLink).toHaveBeenCalledWith("https://bugs");

    fireEvent.click(
      screen.getByTestId("canvas_controls_dropdown_get_flow_desktop"),
    );
    expect(openLink).toHaveBeenCalledWith("https://desktop");

    fireEvent.click(
      screen.getByTestId("canvas_controls_dropdown_enable_smart_guides"),
    );
    expect(onToggleHelperLines).toHaveBeenCalled();
  });
});
