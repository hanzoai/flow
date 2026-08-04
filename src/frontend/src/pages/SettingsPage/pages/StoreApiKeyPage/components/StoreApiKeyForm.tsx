import { useTranslation } from "react-i18next";
import InputComponent from "../../../../../components/core/parameterRenderComponent/components/inputComponent";
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@hanzo/ui";

type StoreApiKeyFormComponentProps = {
  apikey: string;
  handleInput: (event: any) => void;
  handleSaveKey: (apikey: string, handleInput: any) => void;
  loadingApiKey: boolean;
  validApiKey: boolean;
  hasApiKey: boolean;
};
const StoreApiKeyFormComponent = ({
  apikey,
  handleInput,
  handleSaveKey,
  loadingApiKey,
  validApiKey,
  hasApiKey,
}: StoreApiKeyFormComponentProps) => {
  const { t } = useTranslation();
  return (
    <>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          handleSaveKey(apikey, handleInput);
        }}
      >
        <Card x-chunk="dashboard-04-chunk-2" id="api">
          <CardHeader>
            <CardTitle>Store API Key</CardTitle>
            <CardDescription>
              {(hasApiKey && !validApiKey
                ? t("store.invalidApiKey")
                : !hasApiKey
                  ? t("store.noApiKey")
                  : "") + t("store.insertApiKey")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex w-full flex-col gap-3">
              <div className="flex w-full gap-4">
                <>
                  <InputComponent
                    id="apikey"
                    onChange={(value) => {
                      handleInput({ target: { name: "apikey", value } });
                    }}
                    value={apikey}
                    isForm
                    password={true}
                    placeholder="Insert your API Key"
                    className="w-full"
                  />
                  
                </>
              </div>
              <span className="pr-1 text-xs text-muted-foreground">
                {t("store.createApiKey")}{" "}
                <a
                  className="text-high-indigo underline"
                  href="https://flow.store/"
                  target="_blank"
                  rel="noopener"
                >
                  flow.store
                </a>
              </span>
            </div>
          </CardContent>
          <CardFooter className="border-t px-6 py-4">
            <>
              <Button
                loading={loadingApiKey}
                type="submit"
                data-testid="api-key-save-button-store"
              >
                Save
              </Button>
            </>
          </CardFooter>
        </Card>
      </form>
    </>
  );
};
export default StoreApiKeyFormComponent;
