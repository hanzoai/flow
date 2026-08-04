import { Eye, EyeOff } from "lucide-react";
import { useContext, useEffect, useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button, Checkbox } from "@hanzo/ui";
import { CONTROL_NEW_USER } from "../../constants/constants";
import { AuthContext } from "../../contexts/authContext";
import type {
  inputHandlerEventType,
  UserInputType,
  UserManagementType,
} from "../../types/components";
import BaseModal from "../baseModal";

export default function UserManagementModal({
  title,
  titleHeader,
  cancelText,
  confirmationText,
  children,
  icon,
  data,
  index,
  onConfirm,
  asChild,
}: UserManagementType) {
  const [pwdVisible, setPwdVisible] = useState(false);
  const [confirmPwdVisible, setConfirmPwdVisible] = useState(false);
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState(data?.password ?? "");
  const [username, setUserName] = useState(data?.username ?? "");
  const [confirmPassword, setConfirmPassword] = useState(data?.password ?? "");
  const [isActive, setIsActive] = useState(data?.is_active ?? false);
  const [isSuperUser, setIsSuperUser] = useState(data?.is_superuser ?? false);
  const [inputState, setInputState] = useState<UserInputType>(CONTROL_NEW_USER);
  const { userData } = useContext(AuthContext);

  function handleInput({
    target: { name, value },
  }: inputHandlerEventType): void {
    setInputState((prev) => ({ ...prev, [name]: value }));
  }

  useEffect(() => {
    if (open) {
      if (!data) {
        resetForm();
      } else {
        setUserName(data.username);
        setIsActive(data.is_active);
        setIsSuperUser(data.is_superuser);

        handleInput({ target: { name: "username", value: data.username } });
        handleInput({ target: { name: "is_active", value: data.is_active } });
        handleInput({
          target: { name: "is_superuser", value: data.is_superuser },
        });
      }
    }
  }, [open]);

  function resetForm() {
    setPassword("");
    setUserName("");
    setConfirmPassword("");
    setIsActive(false);
    setIsSuperUser(false);
  }

  return (
    <BaseModal size="medium-h-full" open={open} setOpen={setOpen}>
      <BaseModal.Trigger asChild={asChild}>{children}</BaseModal.Trigger>
      <BaseModal.Header description={titleHeader}>
        <span className="pr-2">{title}</span>
        <IconComponent
          name={icon}
          className="h-6 w-6 pl-1 text-foreground"
          aria-hidden="true"
        />
      </BaseModal.Header>
      <BaseModal.Content>
        <form
          onSubmit={(event) => {
            if (password !== confirmPassword) {
              event.preventDefault();
              return;
            }
            resetForm();
            onConfirm(1, inputState);
            setOpen(false);
            event.preventDefault();
          }}
        >
          <div className="grid gap-5">
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  justifyContent: "space-between",
                }}
              >
                <label className="data-[invalid]:label-invalid">
                  Username{" "}
                  <span className="font-medium text-destructive">*</span>
                </label>
              </div>
              <>
                <input
                  onChange={({ target: { value } }) => {
                    handleInput({ target: { name: "username", value } });
                    setUserName(value);
                  }}
                  value={username}
                  className="primary-input"
                  required
                  placeholder="Username"
                />
              </>
              
            </>

            <div className="flex flex-row">
              <div className="mr-3 basis-1/2">
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      justifyContent: "space-between",
                    }}
                  >
                    <label className="data-[invalid]:label-invalid flex">
                      Password{" "}
                      <span className="ml-1 mr-1 font-medium text-destructive">
                        *
                      </span>
                      {pwdVisible && (
                        <Eye
                          onClick={() => setPwdVisible(!pwdVisible)}
                          className="h-5 cursor-pointer"
                          strokeWidth={1.5}
                        />
                      )}
                      {!pwdVisible && (
                        <EyeOff
                          onClick={() => setPwdVisible(!pwdVisible)}
                          className="h-5 cursor-pointer"
                          strokeWidth={1.5}
                        />
                      )}
                    </label>
                  </div>
                  <>
                    <input
                      onChange={({ target: { value } }) => {
                        handleInput({ target: { name: "password", value } });
                        setPassword(value);
                      }}
                      value={password}
                      className="primary-input"
                      required={data ? false : true}
                      type={pwdVisible ? "text" : "password"}
                    />
                  </>

                  

                  {password != confirmPassword && (
                    
                  )}
                </>
              </div>

              <div className="basis-1/2">
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      justifyContent: "space-between",
                    }}
                  >
                    <label className="data-[invalid]:label-invalid flex">
                      Confirm password{" "}
                      <span className="ml-1 mr-1 font-medium text-destructive">
                        *
                      </span>
                      {confirmPwdVisible && (
                        <Eye
                          onClick={() =>
                            setConfirmPwdVisible(!confirmPwdVisible)
                          }
                          className="h-5 cursor-pointer"
                          strokeWidth={1.5}
                        />
                      )}
                      {!confirmPwdVisible && (
                        <EyeOff
                          onClick={() =>
                            setConfirmPwdVisible(!confirmPwdVisible)
                          }
                          className="h-5 cursor-pointer"
                          strokeWidth={1.5}
                        />
                      )}
                    </label>
                  </div>
                  <>
                    <input
                      onChange={(input) => {
                        setConfirmPassword(input.target.value);
                      }}
                      value={confirmPassword}
                      className="primary-input"
                      required={data ? false : true}
                      type={confirmPwdVisible ? "text" : "password"}
                    />
                  </>
                  
                </>
              </div>
            </div>
            <div className="flex gap-8">
              <>
                <div>
                  <label className="data-[invalid]:label-invalid mr-3">
                    Active
                  </label>
                  {data?.id === userData?.id ? (
                    <ShadTooltip content="You cannot deactivate your own account">
                      <span className="inline-block cursor-not-allowed">
                        <Checkbox
                          value={isActive}
                          checked={isActive}
                          id="is_active"
                          className="relative top-0.5 pointer-events-none opacity-50"
                          disabled
                        />
                      </span>
                    </ShadTooltip>
                  ) : (
                    <>
                      <Checkbox
                        value={isActive}
                        checked={isActive}
                        id="is_active"
                        className="relative top-0.5"
                        onCheckedChange={(value) => {
                          handleInput({ target: { name: "is_active", value } });
                          setIsActive(value);
                        }}
                      />
                    </>
                  )}
                </div>
              </>
              {userData?.is_superuser && (
                <>
                  <div>
                    <label className="data-[invalid]:label-invalid mr-3">
                      Superuser
                    </label>
                    <>
                      <Checkbox
                        checked={isSuperUser}
                        value={isSuperUser}
                        id="is_superuser"
                        className="relative top-0.5"
                        onCheckedChange={(value) => {
                          handleInput({
                            target: { name: "is_superuser", value },
                          });
                          setIsSuperUser(value);
                        }}
                      />
                    </>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="float-right">
            <Button
              variant="outline"
              onClick={() => {
                setOpen(false);
              }}
              className="mr-3"
            >
              {cancelText}
            </Button>

            <>
              <Button className="mt-8">{confirmationText}</Button>
            </>
          </div>
        </form>
      </BaseModal.Content>
    </BaseModal>
  );
}
