import { describe, expect, it } from "vitest";
import { droneCatalog } from "./droneCatalog";
import { defaultConcept, defaultRequirements, getCalculationProfile, runSimulation } from "./aeroEngine";

describe("AeroMind drone catalog profiles", () => {
  it("contains fifty-six unique editable civil and non-armed defense profiles", () => {
    expect(droneCatalog).toHaveLength(56);
    expect(new Set(droneCatalog.map(design => design.id)).size).toBe(56);
    for (const design of droneCatalog) {
      expect(design.configuration.wingspan ?? 0).toBeGreaterThan(0);
      expect(design.configuration.fuselageLength ?? 0).toBeGreaterThan(0);
      expect(design.configuration.batteryWh ?? 0).toBeGreaterThan(0);
      expect(design.configuration.motorCount ?? 0).toBeGreaterThan(0);
      expect(design.configuration.payloadKg ?? -1).toBeGreaterThanOrEqual(0);
      expect(design.configuration.cruiseSpeedKmh ?? 0).toBeGreaterThan(0);
    }
  });

  it("covers base and specialized architectures with distinct starting configurations", () => {
    expect(droneCatalog.filter(design => design.key === "fixed-wing")).toHaveLength(23);
    expect(droneCatalog.filter(design => design.key === "quadcopter")).toHaveLength(18);
    expect(droneCatalog.filter(design => design.key === "vtol")).toHaveLength(15);
    expect(new Set(droneCatalog.map(design => design.modelType)).size).toBe(20);
    expect(new Set(droneCatalog.map(design => design.configuration.motorCount)).size).toBeGreaterThan(1);
  });

  it("propagates every catalog morphology into the calculation engine", () => {
    for (const design of droneCatalog) {
      const config = { ...defaultConcept, ...design.configuration, airframe: design.key, modelType: design.modelType };
      expect(getCalculationProfile(config).modelType).toBe(design.modelType);
      expect(runSimulation(config, defaultRequirements, `CAT-${design.id}`).estimatedPowerW).toBeGreaterThan(0);
    }
  });

  it("qualifies democratic-defense profiles without weapon payloads", () => {
    const defense = droneCatalog.filter(design => design.role === "défense-non-armée");
    expect(defense).toHaveLength(12);
    expect(defense.every(design => design.defenseUse?.length)).toBe(true);
    expect(defense.every(design => /sans|aucune|capteurs/i.test(design.defenseUse ?? ""))).toBe(true);
    expect(droneCatalog.filter(design => design.origin === "prototype-reference")).toHaveLength(1);
    expect(droneCatalog.find(design => design.id === "deluge-e")?.origin).toBe("prototype-reference");
  });
});
