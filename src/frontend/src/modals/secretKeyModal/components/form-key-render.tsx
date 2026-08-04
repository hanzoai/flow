import { Input, Label } from "@hanzo/ui";

export const FormKeyRender = ({
  modalProps,
  apiKeyName,
  inputRef,
  setApiKeyName,
}: {
  modalProps: any;
  apiKeyName: string;
  inputRef: React.RefObject<HTMLInputElement>;
  setApiKeyName: (value: string) => void;
}) => {
  return (
    <>
      {modalProps?.inputLabel && (
        <label asChild className="mb-2">
          <Label className="relative bottom-1">
            {modalProps?.inputLabel as React.ReactNode}
          </Label>
        </label>
      )}

      <div className="flex items-center justify-between gap-2">
        <>
          <Input
            id="primary-input"
            value={apiKeyName}
            ref={inputRef}
            onChange={({ target: { value } }) => {
              setApiKeyName(value);
            }}
            placeholder={modalProps?.inputPlaceholder}
          />
        </>
      </div>
    </>
  );
};
