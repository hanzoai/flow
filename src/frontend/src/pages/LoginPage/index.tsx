import { useQueryClient } from "@tanstack/react-query";
import { useContext, useState } from "react";
import { useTranslation } from "react-i18next";
import FlowLogo from "@/assets/FlowLogo.svg?react";
import { useLoginUser } from "@/controllers/API/queries/auth";
import { CustomLink } from "@/customization/components/custom-link";
import { useSanitizeRedirectUrl } from "@/hooks/use-sanitize-redirect-url";
import InputComponent from "../../components/core/parameterRenderComponent/components/inputComponent";
import { Button, Input } from "@hanzo/ui";
import { CONTROL_LOGIN_STATE, IS_AUTO_LOGIN } from "../../constants/constants";
import { AuthContext } from "../../contexts/authContext";
import useAlertStore from "../../stores/alertStore";
import type { LoginType } from "../../types/api";
import type {
  inputHandlerEventType,
  loginInputStateType,
} from "../../types/components";

export default function LoginPage(): JSX.Element {
  const [inputState, setInputState] =
    useState<loginInputStateType>(CONTROL_LOGIN_STATE);

  const { password, username } = inputState;

  useSanitizeRedirectUrl();

  const { t } = useTranslation();
  const { login, clearAuthSession } = useContext(AuthContext);
  const setErrorData = useAlertStore((state) => state.setErrorData);

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

  return (
    <form
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
      <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
        <div className="flex w-72 flex-col items-center justify-center gap-2">
          <FlowLogo
            title="HanzoFlow logo"
            className="mb-4 h-10 w-10 scale-[1.5]"
          />
          <span className="mb-6 text-2xl font-semibold text-primary">
            Sign in to HanzoFlow
          </span>
          <div className="mb-3 w-full">
            <>
              <label className="data-[invalid]:label-invalid">
                {t("auth.usernameLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </label>

              <>
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
              </>

              
            </>
          </div>
          <div className="mb-3 w-full">
            <>
              <label className="data-[invalid]:label-invalid">
                {t("auth.passwordLabel")}{" "}
                <span className="font-medium text-destructive">*</span>
              </label>

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

              
            </>
          </div>
          <div className="w-full">
            <>
              <Button className="mr-3 mt-6 w-full" type="submit">
                {t("auth.signInButton")}
              </Button>
            </>
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
    </form>
  );
}
