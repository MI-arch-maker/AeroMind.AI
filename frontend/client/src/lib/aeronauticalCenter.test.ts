import { describe, expect, it } from "vitest";
import { defaultConcept } from "./aeroEngine";
import { equipmentOptions, evaluateReadiness } from "./aeronauticalCenter";

describe("aeronautical center readiness", () => {
  it("keeps an incomplete aircraft configuration blocked", () => {
    const result = evaluateReadiness(defaultConcept, [], "observation");
    expect(result.status).toBe("blocked");
    expect(result.passed).toBe(3);
  });
  it("recognizes a configured non-armed observation aircraft", () => {
    const config = { ...defaultConcept, airframe: "quadcopter" as const, batteryWh: 900, reserveFraction: 0.2, maxTakeoffKg: 8 };
    const equipment = equipmentOptions.filter(item => ["eo-gimbal", "rtk", "parachute"].includes(item.id));
    const result = evaluateReadiness(config, equipment, "observation");
    expect(result.status).toBe("ready");
    expect(result.passed).toBe(result.total);
  });
});
