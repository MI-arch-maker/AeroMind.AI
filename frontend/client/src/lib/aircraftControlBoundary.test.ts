import { describe, expect, it } from "vitest";
import {
  authorizeControlCommand,
  CONTROL_BOUNDARY,
  createControlAuditEvent,
  ingestReadOnlyTelemetry,
} from "./aircraftControlBoundary";

describe("aircraft control boundary", () => {
  const command = (kind: Parameters<typeof authorizeControlCommand>[0]["kind"]) => ({
    kind,
    operator: "test-operator",
    requestedAt: new Date(0).toISOString(),
  });

  it("keeps real hardware capabilities disabled", () => {
    expect(CONTROL_BOUNDARY.hardwareControlEnabled).toBe(false);
    expect(CONTROL_BOUNDARY.telemetryWriteEnabled).toBe(false);
    expect(CONTROL_BOUNDARY.missionUploadEnabled).toBe(false);
  });

  it.each(["actuator-write", "arm", "mission-upload"] as const)(
    "rejects %s in every transport",
    kind => {
      expect(authorizeControlCommand(command(kind), "simulation").accepted).toBe(false);
      expect(authorizeControlCommand(command(kind), "hil").accepted).toBe(false);
      expect(authorizeControlCommand(command(kind), "hardware-readonly").accepted).toBe(false);
    }
  );

  it("accepts a simulation command without creating a hardware path", () => {
    const decision = authorizeControlCommand(command("simulation-return"));
    expect(decision).toMatchObject({ accepted: true, mode: "simulation" });
    expect(createControlAuditEvent(decision, "CTRL-TEST")).toMatchObject({ id: "CTRL-TEST", command: "simulation-return" });
  });

  it("allows observation only in hardware-readonly mode", () => {
    expect(authorizeControlCommand(command("observe"), "hardware-readonly").accepted).toBe(true);
    expect(authorizeControlCommand(command("simulation-hold"), "hardware-readonly").accepted).toBe(false);
  });

  it("validates telemetry as read-only input", () => {
    expect(ingestReadOnlyTelemetry(JSON.stringify({ telemetry: { altitudeM: 42, batteryPct: 80 } }))).toMatchObject({ accepted: true, frame: { altitudeM: 42, batteryPct: 80 } });
    expect(ingestReadOnlyTelemetry("bad-json")).toMatchObject({ accepted: false, frame: null });
  });
});
