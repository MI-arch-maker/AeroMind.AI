export const WORKSPACE_SYNC_CHANNEL = "aeromind-workspace-sync";
export const LABBENCH_STATE_KEY = "aeromind-labbench-state-v1";

export type WorkspaceSyncMessage =
  | { type: "workspace"; payload: unknown }
  | { type: "view"; view: string }
  | { type: "labbench"; payload: unknown };

export function createWorkspaceChannel(): BroadcastChannel | null {
  if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") return null;
  return new BroadcastChannel(WORKSPACE_SYNC_CHANNEL);
}

export function publishWorkspaceMessage(channel: BroadcastChannel | null, message: WorkspaceSyncMessage) {
  if (typeof window === "undefined") return;
  try {
    channel?.postMessage(message);
  } catch {
    // Le stockage local reste le repli fiable si BroadcastChannel est indisponible.
  }
}

export function persistAndPublish<T>(key: string, value: T, channel: BroadcastChannel | null, message: WorkspaceSyncMessage) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Un stockage navigateur plein ne doit pas bloquer l’interface courante.
  }
  publishWorkspaceMessage(channel, message);
}

export function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
