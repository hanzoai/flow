import ForwardedIconComponent from "../../../../../../components/common/genericIconComponent";

const GeneralPageHeaderComponent = () => {
  return (
    <div className="flex w-full items-center justify-between gap-4 space-y-0.5">
      <div className="flex w-full flex-col">
        <h2
          className="flex items-center text-lg font-semibold tracking-tight"
          data-testid="settings_menu_header"
        >
          Account &amp; Organization
          <ForwardedIconComponent
            name="Building2"
            className="ml-2 h-5 w-5 text-primary"
          />
        </h2>
        <p className="text-sm text-muted-foreground">
          Managed by Hanzo IAM. Switch active organization, create workspaces, or
          update your profile and billing on hanzo.ai.
        </p>
      </div>
    </div>
  );
};

export default GeneralPageHeaderComponent;
