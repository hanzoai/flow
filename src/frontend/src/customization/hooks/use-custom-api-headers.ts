import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useIamStore } from "@/stores/iamStore";

export function useCustomApiHeaders(): Record<string, string> {
  const { i18n } = useTranslation();
  const activeOrg = useIamStore((state) => state.activeOrg);

  return useMemo(() => {
    const headers: Record<string, string> = {
      "Accept-Language": i18n.language || "en",
    };
    if (activeOrg) {
      headers["X-Org-Id"] = activeOrg;
      headers["X-IAM-Org-Id"] = activeOrg;
    }
    return headers;
  }, [i18n.language, activeOrg]);
}
