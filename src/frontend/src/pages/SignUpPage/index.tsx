import { useEffect } from "react";
import FlowLogo from "@/assets/FlowLogo.svg?react";

export default function SignUp(): JSX.Element {
  useEffect(() => {
    window.location.replace("/v1/iam/login");
  }, []);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-background">
      <FlowLogo
        title="Hanzo Flow"
        className="h-12 w-12 text-foreground opacity-80"
      />
    </div>
  );
}
