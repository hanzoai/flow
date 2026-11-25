import { create } from "zustand";

export interface IamOrgSummary {
  name: string;
  display_name: string;
  role: string;
  is_personal: boolean;
  is_member: boolean;
  logo: string;
  favicon: string;
  website_url: string;
  plan: string;
}

export interface IamUserProfile {
  id: string;
  sub: string;
  did: string;
  username: string;
  display_name: string;
  email: string;
  picture: string;
  owner: string;
  is_super_admin: boolean;
}

export interface IamLinks {
  account: string;
  billing: string;
  organizations: string;
  app: string;
  docs: string;
}

export interface IamContext {
  iam_enabled: boolean;
  issuer: string;
  user: IamUserProfile;
  active_org: string;
  active_org_info: IamOrgSummary | null;
  orgs: IamOrgSummary[];
  links: IamLinks;
}

const ACTIVE_ORG_STORAGE_KEY = "hanzo_flow_active_org";

function readStoredOrg(): string | null {
  try {
    const val = window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY);
    return val && val.trim() ? val.trim() : null;
  } catch {
    return null;
  }
}

function writeStoredOrg(org: string | null): void {
  try {
    if (org && org.trim()) {
      window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, org.trim());
    } else {
      window.localStorage.removeItem(ACTIVE_ORG_STORAGE_KEY);
    }
  } catch {
    // Ignore storage quota / private mode failures
  }
}

export function getInitials(name?: string | null): string {
  const raw = (name ?? "").trim();
  if (!raw) return "?";
  const parts = raw
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2);
  if (parts.length === 0) return "?";
  return parts.map((p) => p.charAt(0).toUpperCase()).join("");
}

export function cleanAvatarUrl(url?: string | null): string | null {
  const trimmed = (url ?? "").trim();
  if (!trimmed) return null;
  if (
    trimmed.includes("gravatar.com/avatar/") &&
    trimmed.includes("d=identicon")
  ) {
    return null;
  }
  return trimmed;
}

export function orgSlugPreview(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

interface IamStoreState {
  context: IamContext | null;
  activeOrg: string | null;
  isSwitchingOrg: boolean;
  setContext: (ctx: IamContext | null) => void;
  setActiveOrg: (org: string | null) => void;
  setIsSwitchingOrg: (switching: boolean) => void;
  reset: () => void;
}

export const useIamStore = create<IamStoreState>((set) => ({
  context: null,
  activeOrg: readStoredOrg(),
  isSwitchingOrg: false,

  setContext: (ctx) => {
    const resolvedOrg = ctx?.active_org || null;
    if (resolvedOrg) {
      writeStoredOrg(resolvedOrg);
    }
    set((state) => ({
      context: ctx,
      activeOrg: resolvedOrg ?? state.activeOrg,
    }));
  },

  setActiveOrg: (org) => {
    const clean = org?.trim() || null;
    writeStoredOrg(clean);
    set({ activeOrg: clean });
  },

  setIsSwitchingOrg: (isSwitchingOrg) => set({ isSwitchingOrg }),

  reset: () => {
    writeStoredOrg(null);
    set({ context: null, activeOrg: null, isSwitchingOrg: false });
  },
}));

export default useIamStore;
