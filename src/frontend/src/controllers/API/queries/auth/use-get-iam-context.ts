import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import useAlertStore from "@/stores/alertStore";
import useAuthStore from "@/stores/authStore";
import useFlowStore from "@/stores/flowStore";
import useFlowsManagerStore from "@/stores/flowsManagerStore";
import { useFolderStore } from "@/stores/foldersStore";
import { type IamContext, useIamStore } from "@/stores/iamStore";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";

export const IAM_CONTEXT_QUERY_KEY = ["useGetIamContext"] as const;

export function useGetIamContext() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const setContext = useIamStore((state) => state.setContext);

  return useQuery<IamContext | null>({
    queryKey: IAM_CONTEXT_QUERY_KEY,
    queryFn: async () => {
      try {
        const response = await api.get<IamContext>(getURL("IAM_CONTEXT"));
        setContext(response.data);
        return response.data;
      } catch {
        // Gracefully fall back to local / single-org mode without noisy console errors
        return null;
      }
    },
    enabled: Boolean(isAuthenticated),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  });
}

async function refreshWorkspaceAfterOrgChange(
  queryClient: ReturnType<typeof useQueryClient>,
  nextContext: IamContext,
) {
  useIamStore.getState().setContext(nextContext);
  queryClient.setQueryData(IAM_CONTEXT_QUERY_KEY, nextContext);

  useFlowStore.getState().resetFlowState();
  useFlowsManagerStore.getState().resetStore();
  useFolderStore.getState().resetStore();

  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["useGetFolders"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetFolder"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetFlows"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetKnowledgeBases"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetGlobalVariables"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetEnabledModels"] }),
    queryClient.invalidateQueries({ queryKey: ["useGetModelProviders"] }),
  ]);
}

export function useSwitchIamOrg() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setIsSwitchingOrg = useIamStore((state) => state.setIsSwitchingOrg);

  return useMutation<IamContext, Error, string>({
    mutationFn: async (org: string) => {
      setIsSwitchingOrg(true);
      const response = await api.post<IamContext>(getURL("IAM_ORG"), { org });
      return response.data;
    },
    onSuccess: async (nextContext) => {
      await refreshWorkspaceAfterOrgChange(queryClient, nextContext);
      const label =
        nextContext.active_org_info?.display_name || nextContext.active_org;
      setSuccessData({ title: `Switched organization to ${label}` });
      if (
        location.pathname.startsWith("/flow/") ||
        location.pathname.includes("/folder/")
      ) {
        navigate("/flows");
      }
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "Could not switch organization.";
      setErrorData({ title: "Organization switch failed", list: [detail] });
    },
    onSettled: () => {
      setIsSwitchingOrg(false);
    },
  });
}

export interface CreateIamOrgResponse {
  org: string;
  display_name: string;
  context: IamContext;
}

export function useCreateIamOrg() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  return useMutation<CreateIamOrgResponse, Error, string>({
    mutationFn: async (name: string) => {
      const response = await api.post<CreateIamOrgResponse>(
        getURL("IAM_ORGS"),
        { name },
      );
      return response.data;
    },
    onSuccess: async (data) => {
      await refreshWorkspaceAfterOrgChange(queryClient, data.context);
      setSuccessData({
        title: `Created organization "${data.display_name}"`,
      });
      if (
        location.pathname.startsWith("/flow/") ||
        location.pathname.includes("/folder/")
      ) {
        navigate("/flows");
      }
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "Could not create organization.";
      setErrorData({ title: "Create organization failed", list: [detail] });
    },
  });
}
