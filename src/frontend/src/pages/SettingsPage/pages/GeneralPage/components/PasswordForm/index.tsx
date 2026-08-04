import { useTranslation } from "react-i18next";
import InputComponent from "../../../../../../components/core/parameterRenderComponent/components/inputComponent";
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@hanzo/ui";

type PasswordFormComponentProps = {
  password: string;
  cnfPassword: string;
  handleInput: (event: any) => void;
  handlePatchPassword: (
    password: string,
    cnfPassword: string,
    handleInput: any,
  ) => void;
};
const PasswordFormComponent = ({
  password,
  cnfPassword,
  handleInput,
  handlePatchPassword,
}: PasswordFormComponentProps) => {
  const { t } = useTranslation();
  return (
    <>
      <form
        onSubmit={(event) => {
          handlePatchPassword(password, cnfPassword, handleInput);
          event.preventDefault();
        }}
      >
        <Card x-chunk="dashboard-04-chunk-2">
          <CardHeader>
            <CardTitle>{t("settings.passwordTitle")}</CardTitle>
            <CardDescription>
              {t("settings.passwordDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex w-full gap-4">
              <>
                <InputComponent
                  id="pasword"
                  onChange={(value) => {
                    handleInput({ target: { name: "password", value } });
                  }}
                  value={password}
                  isForm
                  password={true}
                  placeholder={t("settings.passwordPlaceholder")}
                  className="w-full"
                />
                
              </>
              <>
                <InputComponent
                  id="cnfPassword"
                  onChange={(value) => {
                    handleInput({
                      target: { name: "cnfPassword", value },
                    });
                  }}
                  value={cnfPassword}
                  isForm
                  password={true}
                  placeholder={t("settings.confirmPasswordPlaceholder")}
                  className="w-full"
                />

                
              </>
            </div>
          </CardContent>
          <CardFooter className="border-t px-6 py-4">
            <>
              <Button type="submit">{t("settings.saveButton")}</Button>
            </>
          </CardFooter>
        </Card>
      </form>
    </>
  );
};
export default PasswordFormComponent;
