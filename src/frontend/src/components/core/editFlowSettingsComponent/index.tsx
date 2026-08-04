import type React from "react";
import { useState } from "react";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Switch } from "@hanzo/ui";
import type { InputProps } from "../../../types/components";
import { cn } from "../../../utils/utils";
import { Input } from "../../ui/input";
import { Textarea } from "../../ui/textarea";

export const EditFlowSettings: React.FC<
  InputProps & {
    submitForm?: () => void;
    locked?: boolean;
    setLocked?: (v: boolean) => void;
  }
> = ({
  name,
  invalidNameList = [],
  description,
  maxLength = 50,
  descriptionMaxLength = 250,
  minLength = 1,
  setName,
  setDescription,
  submitForm,
  locked = false,
  setLocked,
}: InputProps & {
  submitForm?: () => void;
  locked?: boolean;
  setLocked?: (v: boolean) => void;
}): JSX.Element => {
  const [isMaxLength, setIsMaxLength] = useState(false);
  const [isMaxDescriptionLength, setIsMaxDescriptionLength] = useState(false);
  const [isMinLength, setIsMinLength] = useState(false);
  const [isInvalidName, setIsInvalidName] = useState(false);

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    if (value.length >= maxLength) {
      setIsMaxLength(true);
    } else {
      setIsMaxLength(false);
    }
    if (value.length < minLength) {
      setIsMinLength(true);
    } else {
      setIsMinLength(false);
    }
    let invalid = false;
    for (let i = 0; i < invalidNameList!.length; i++) {
      if (value === invalidNameList![i]) {
        invalid = true;
        break;
      }
      invalid = false;
    }
    setIsInvalidName(invalid);
    setName!(value);
    if (value.length === 0) {
      setIsMinLength(true);
    }
  };

  const handleDescriptionChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ) => {
    const { value } = event.target;
    if (value.length >= descriptionMaxLength) {
      setIsMaxDescriptionLength(true);
    } else {
      setIsMaxDescriptionLength(false);
    }
    setDescription!(value);
  };

  const handleDescriptionKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (submitForm) submitForm();
    }
    // else allow default (newline)
  };

  const handleFocus = (event) => event.target.select();

  return (
    <>
      <>
        <div className="edit-flow-arrangement">
          <label className="text-mmd font-medium">
            Name{setName ? "" : ":"}
          </label>
          {isMaxLength && (
            <span className="edit-flow-span">Character limit reached</span>
          )}
          {isMinLength && (
            <span className="edit-flow-span">
              Minimum {minLength} character(s) required
            </span>
          )}
          {isInvalidName && (
            <span className="edit-flow-span">Flow name already exists</span>
          )}
        </div>
        {setName ? (
          <>
            <Input
              className="nopan nodelete nodrag noflow mt-2 font-normal"
              onChange={handleNameChange}
              type="text"
              name="name"
              value={name ?? ""}
              placeholder="Flow name"
              id="name"
              maxLength={maxLength}
              minLength={minLength}
              required={true}
              onDoubleClickCapture={handleFocus}
              data-testid="input-flow-name"
              autoFocus
              disabled={locked}
            />
          </>
        ) : (
          <span className="font-normal text-muted-foreground word-break-break-word">
            {name}
          </span>
        )}
        
        
      </>
      <>
        <div className="edit-flow-arrangement mt-2">
          <label className="text-mmd font-medium">
            Description{setDescription ? "" : ":"}
          </label>
          {isMaxDescriptionLength && (
            <span className="edit-flow-span">Character limit reached</span>
          )}
        </div>
        {setDescription ? (
          <>
            <Textarea
              name="description"
              id="description"
              onChange={handleDescriptionChange}
              value={description!}
              placeholder="Flow description"
              data-testid="input-flow-description"
              className="mt-2 max-h-[250px] resize-none font-normal"
              rows={5}
              maxLength={descriptionMaxLength}
              onDoubleClickCapture={handleFocus}
              onKeyDown={handleDescriptionKeyDown}
              disabled={locked}
            />
          </>
        ) : (
          <div
            className={cn(
              "max-h-[250px] overflow-auto pt-2 font-normal text-muted-foreground word-break-break-word",
              description === "" ? "font-light italic" : "",
            )}
          >
            {description === "" ? "No description" : description}
          </div>
        )}
        
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <div>
              <div className="flex items-center gap-2">
                <label className="text-mmd font-medium">
                  Lock Flow
                </label>

                <ForwardedIconComponent
                  name={locked ? "Lock" : "Unlock"}
                  className="text-muted-foreground !w-5 !h-5"
                />
              </div>

              <p className="text-xs text-muted-foreground/70 mt-1 font-normal">
                Lock your flow to prevent edits or accidental changes.
              </p>
            </div>

            <Switch
              checked={!!locked}
              onCheckedChange={(v) => setLocked?.(v)}
              className="data-[state=checked]:bg-primary ml-auto"
              data-testid="lock-flow-switch"
            />
          </div>
        </div>
      </>
    </>
  );
};

export default EditFlowSettings;
