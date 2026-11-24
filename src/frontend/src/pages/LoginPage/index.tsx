import * as Form from "@radix-ui/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import FlowLogo from "@/assets/FlowLogo.svg?react";
import { useLoginUser } from "@/controllers/API/queries/auth";
import { CustomLink } from "@/customization/components/custom-link";
import { useSanitizeRedirectUrl } from "@/hooks/use-sanitize-redirect-url";
import InputComponent from "../../components/core/parameterRenderComponent/components/inputComponent";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { CONTROL_LOGIN_STATE } from "../../constants/constants";
import { AuthContext } from "../../contexts/authContext";
import useAlertStore from "../../stores/alertStore";
import type { LoginType } from "../../types/api";
import type {
  inputHandlerEventType,
  loginInputStateType,
} from "../../types/components";

type IamConfig = {
  enabled: boolean;
  login_url?: string;
};

export default function LoginPage(): JSX.Element {
  const [inputState, setInputState] =
    useState<loginInputStateType>(CONTROL_LOGIN_STATE);
  const [iamConfig, setIamConfig] = useState<IamConfig | null>(null);

  const { password, username } = inputState;

  useSanitizeRedirectUrl();

  const { t } = useTranslation();
  const { login, clearAuthSession } = useContext(AuthContext);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const searchParams = new URLSearchParams(window.location.search);
  const redirectParam = searchParams.get("redirect");
  const authError = searchParams.get("error");

  useEffect(() => {
    let cancelled = false;
    fetch("/v1/iam/config", { credentials: "same-origin" })
      .then((res) => (res.ok ? res.json() : { enabled: false }))
      .then((data: IamConfig) => {
        if (!cancelled) setIamConfig(data?.enabled ? data : { enabled: false });
      })
      .catch(() => {
        if (!cancelled) setIamConfig({ enabled: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleInput({
    target: { name, value },
  }: inputHandlerEventType): void {
    setInputState((prev) => ({ ...prev, [name]: value }));
  }

  const { mutate } = useLoginUser();
  const queryClient = useQueryClient();

  function signIn() {
    const user: LoginType = {
      username: username.trim(),
      password: password.trim(),
    };

    mutate(user, {
      onSuccess: (data) => {
        clearAuthSession();
        login(data.access_token, "login", data.refresh_token);
        queryClient.clear();
      },
      onError: (error) => {
        setErrorData({
          title: t("errors.signin"),
          list: [error["response"]["data"]["detail"]],
        });
      },
    });
  }

  function startIamSignIn() {
    const base = iamConfig?.login_url || "/v1/iam/login";
    const qs = redirectParam
      ? `?redirect=${encodeURIComponent(redirectParam)}`
      : "";
    window.location.assign(`${base}${qs}`);
  }

  // Avoid flashing the local password form while discovering IAM SSO mode.
  if (iamConfig === null) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center bg-background">
        <FlowLogo
          title="Hanzo Flow"
          className="h-12 w-12 text-foreground opacity-80"
        />
      </div>
    );
  }

  if (iamConfig.enabled) {
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
          <Button
            type="button"
            className="w-full"
            onClick={startIamSignIn}
          >
            Continue with Hanzo
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Form.Root
      onSubmit={(event) => {
        if (password === "") {
          event.preventDefault();
          return;
        }
        signIn();
        const _data = Object.fromEntries(new FormData(event.currentTarget));
        event.preventDefault();
      }}
      className="h-screen w-full"
    >
      <div className="flex h-full w-full flex-col items-center justify-center bg-background">
        <div className="flex w-72 flex-col items-center justify-center gap-2">
          <FlowLogo
            title="Hanzo Flow"
            className="mb-4 h-12 w-12 text-foreground"
          />
          <span className="mb-6 text-2xl font-semibold text-primary">
            Sign in to Hanzo Flow
          </span>
          <div className="mb-3 w-full">
            <Form.Field name="username">
              <Form.Label className="data-[invalid]:label-invalid">
                {t("auth.usernameLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </Form.Label>

              <Form.Control asChild>
                <Input
                  type="username"
                  onChange={({ target: { value } }) => {
                    handleInput({ target: { name: "username", value } });
                  }}
                  value={username}
                  className="w-full"
                  required
                  placeholder={t("auth.usernamePlaceholder")}
                />
              </Form.Control>

              <Form.Message match="valueMissing" className="field-invalid">
                {t("auth.usernameRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="mb-3 w-full">
            <Form.Field name="password">
              <Form.Label className="data-[invalid]:label-invalid">
                {t("auth.passwordLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </Form.Label>

              <InputComponent
                onChange={(value) => {
                  handleInput({ target: { name: "password", value } });
                }}
                value={password}
                isForm
                password={true}
                required
                placeholder={t("auth.passwordPlaceholder")}
                className="w-full"
              />

              <Form.Message className="field-invalid" match="valueMissing">
                {t("auth.passwordRequired")}
              </Form.Message>
            </Form.Field>
          </div>
          <div className="w-full">
            <Form.Submit asChild>
              <Button className="mr-3 mt-6 w-full" type="submit">
                {t("auth.signInButton")}
              </Button>
            </Form.Submit>
          </div>
          <div className="w-full">
            <CustomLink to="/signup">
              <Button className="w-full" variant="outline" type="button">
                {t("auth.noAccount")}&nbsp;<b>{t("auth.signUpLink")}</b>
              </Button>
            </CustomLink>
          </div>
        </div>
      </div>
    </Form.Root>
  );
}
