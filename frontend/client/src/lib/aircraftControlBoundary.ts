import { parseMissionTelemetryPayload, type MissionTelemetryFrame } from "./missionBridge";

export type ControlTransport = "simulation" | "hil" | "hardware-readonly";
export type ControlCommandKind =
  | "observe"
  | "simulation-start"
  | "simulation-pause"
  | "simulation-hold"
  | "simulation-return"
  | "simulation-land"
  /** Armement virtuel du scénario local : état d'interface, aucune sortie actionneur. */
  | "simulation-arm"
  /** Désarmement virtuel : retour au banc au sol simulé. */
  | "simulation-disarm"
  | "actuator-write"
  | "arm"
  | "mission-upload";

export type ControlCommand = {
  kind: ControlCommandKind;
  requestedAt: string;
  operator: string;
  payload?: Record<string, unknown>;
};

export type ControlDecision = {
  accepted: boolean;
  mode: ControlTransport;
  reason: string;
  command: ControlCommandKind;
};

export type ControlAuditEvent = ControlDecision & { id: string; timestamp: string };

/**
 * Contrat de sécurité volontairement fermé. Les sorties vers un aéronef réel
 * ne sont pas activables par l'interface et ne doivent pas être ajoutées par
 * une simple variable de configuration.
 */
export const CONTROL_BOUNDARY = {
  version: "control-boundary-v1",
  hardwareControlEnabled: false,
  telemetryWriteEnabled: false,
  missionUploadEnabled: false,
  allowedTransports: ["simulation", "hil", "hardware-readonly"] as const,
  /** L'armement virtuel ne quitte jamais le scénario local. */
  virtualArmingScope: "simulation-only" as const,
  deniedCommands: ["actuator-write", "arm", "mission-upload"] as const,
};

const simulationCommands = new Set<ControlCommandKind>([
  "observe",
  "simulation-start",
  "simulation-pause",
  "simulation-hold",
  "simulation-return",
  "simulation-land",
  "simulation-arm",
  "simulation-disarm",
]);

export function authorizeControlCommand(
  command: ControlCommand,
  transport: ControlTransport = "simulation"
): ControlDecision {
  if (command.kind === "arm" || command.kind === "actuator-write" || command.kind === "mission-upload") {
    return {
      accepted: false,
      mode: transport,
      command: command.kind,
      reason: "Commande rejetée par la frontière AeroMind : aucune sortie de commande réelle n’est activée.",
    };
  }
  if (transport === "hardware-readonly" && command.kind !== "observe") {
    return {
      accepted: false,
      mode: transport,
      command: command.kind,
      reason: "Mode matériel lecture seule : seules les observations sont autorisées.",
    };
  }
  // L'armement virtuel n'est accepté que dans le transport de simulation : il
  // modifie l'état d'interface et les couches de vision, jamais un actionneur.
  if (
    (command.kind === "simulation-arm" || command.kind === "simulation-disarm") &&
    transport !== "simulation"
  ) {
    return {
      accepted: false,
      mode: transport,
      command: command.kind,
      reason: "L’armement virtuel est borné au transport de simulation local.",
    };
  }
  if (!simulationCommands.has(command.kind)) {
    return {
      accepted: false,
      mode: transport,
      command: command.kind,
      reason: "Commande inconnue ou non déclarée dans le contrat de contrôle.",
    };
  }
  return {
    accepted: true,
    mode: transport,
    command: command.kind,
    reason: transport === "simulation"
      ? "Commande acceptée uniquement dans le scénario local.": "Observation acceptée; aucune écriture vers le matériel.",
  };
}

export function ingestReadOnlyTelemetry(raw: unknown): {
  accepted: boolean;
  frame: MissionTelemetryFrame | null;
  reason: string;
} {
  const frame = parseMissionTelemetryPayload(raw);
  return frame
    ? { accepted: true, frame, reason: "Trame validée; lecture seule." }
    : { accepted: false, frame: null, reason: "Trame rejetée : JSON ou unités hors contrat." };
}

export function createControlAuditEvent(decision: ControlDecision, id = `CTRL-${Date.now()}`): ControlAuditEvent {
  return { ...decision, id, timestamp: new Date().toISOString() };
}
