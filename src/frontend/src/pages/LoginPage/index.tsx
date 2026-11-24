import FlowLogo from "@/assets/FlowLogo.svg?react";
import { useSanitizeRedirectUrl } from "@/hooks/use-sanitize-redirect-url";
import { Button } from "../../components/ui/button";

export default function LoginPage(): JSX.Element {
  useSanitizeRedirectUrl();

  const searchParams = new URLSearchParams(window.location.search);
  const redirectParam = searchParams.get("redirect");
  const authError = searchParams.get("error");

  function startIamSignIn() {
    const qs = redirectParam
      ? `?redirect=${encodeURIComponent(redirectParam)}`
      : "";
    window.location.assign(`/v1/iam/login${qs}`);
  }

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-background px-4">
      <div className="flex w-80 flex-col items-center justify-center gap-3 text-center">
        <FlowLogo
          title="Hanzo Flow"
          className="mb-3 h-12 w-12 text-foreground"
        />
        <h1 className="text-2xl font-semibold tracking-tight text-primary">
          Sign in to Hanzo Flow
        </h1>
        <p className="mb-3 text-sm text-muted-foreground">
          Use your Hanzo account to continue.
        </p>
        {authError && (
          <div
            role="alert"
            className="mb-2 w-full rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          >
            Sign-in failed ({authError.replace(/_/g, " ")}). Please try again.
          </div>
        )}
        <Button type="button" className="w-full" onClick={startIamSignIn}>
          Continue with Hanzo
        </Button>
      </div>
    </div>
  );
}
