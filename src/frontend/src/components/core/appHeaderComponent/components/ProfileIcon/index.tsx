import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/contexts/authContext";
import {
  cleanAvatarUrl,
  getInitials,
  useIamStore,
} from "@/stores/iamStore";
import { cn } from "@/utils/utils";

interface ProfileIconProps {
  className?: string;
}

export function ProfileIcon({ className }: ProfileIconProps = {}) {
  const { userData } = useContext(AuthContext);
  const iamUser = useIamStore((state) => state.context?.user);
  const [imgFailed, setImgFailed] = useState(false);

  const avatarUrl = cleanAvatarUrl(iamUser?.picture);
  useEffect(() => {
    setImgFailed(false);
  }, [avatarUrl]);

  const label =
    iamUser?.display_name ||
    iamUser?.email ||
    iamUser?.username ||
    userData?.username ||
    "User";

  if (avatarUrl && !imgFailed) {
    return (
      <img
        src={avatarUrl}
        alt={label}
        onError={() => setImgFailed(true)}
        className={cn(
          "h-6 w-6 shrink-0 rounded-full border border-border object-cover focus-visible:outline-0",
          className,
        )}
      />
    );
  }

  return (
    <span
      aria-label={label}
      className={cn(
        "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[11px] font-semibold text-foreground select-none focus-visible:outline-0",
        className,
      )}
    >
      {getInitials(label)}
    </span>
  );
}
