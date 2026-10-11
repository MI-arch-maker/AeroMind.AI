import { describe, expect, it } from "vitest";
import { parseMissionTelemetryPayload } from "./missionBridge";

describe("read-only mission telemetry bridge", () => {
  it("parses normalized aliases and nested telemetry frames", () => {
    expect(
      parseMissionTelemetryPayload(
        JSON.stringify({
          type: "telemetry",
          telemetry: {
            lat: 48.123456,
            lon: 2.654321,
            altitudeM: 63.5,
            speedKmh: 28,
            batteryPct: 74,
            headingDeg: 182,
            mode: "AUTO",
          },
        })
      )
    ).toEqual({
      latitude: 48.123456,
      longitude: 2.654321,
      altitudeM: 63.5,
      speedKmh: 28,
      batteryPct: 74,
      headingDeg: 182,
      flightMode: "AUTO",
    });
  });

  it("keeps zero-valued readings and rejects out-of-range GPS/battery values", () => {
    expect(
      parseMissionTelemetryPayload(
        JSON.stringify({
          lat: 95,
          lon: -181,
          altitudeM: 0,
          speedKmh: 0,
          batteryPct: 120,
          headingDeg: 0,
        })
      )
    ).toEqual({ altitudeM: 0, speedKmh: 0, headingDeg: 0 });
  });

  it("returns null for malformed frames and objects without supported telemetry", () => {
    expect(parseMissionTelemetryPayload("not-json")).toBeNull();
    expect(
      parseMissionTelemetryPayload(JSON.stringify({ event: "heartbeat" }))
    ).toBeNull();
    expect(parseMissionTelemetryPayload({ altitudeM: 10 })).toBeNull();
  });
});
