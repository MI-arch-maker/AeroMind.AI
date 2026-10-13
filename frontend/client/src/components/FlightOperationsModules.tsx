import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, ClipboardList, Map, Radio, Thermometer, Waypoints } from "lucide-react";
import type { LocalMissionPlan, MissionEnvironment, MissionWaypoint } from "../lib/aeroEngine";
import type { MissionTelemetryFrame } from "../lib/missionBridge";
import "./flight-operations.css";

type Sample = { t: number; speed: number; altitude: number; pitch: number; roll: number; battery: number };
type LogEntry = { time: string; level: "INFO" | "WARN" | "SIM"; event: string; detail: string };
type Props = {
  demoState: string;
  activeWaypoint: number;
  waypoints: LocalMissionPlan["waypoints"];
  missionPlan: LocalMissionPlan;
  environment: MissionEnvironment;
  enduranceH: number;
  batteryWh: number;
  telemetryState: string;
  telemetry?: MissionTelemetryFrame & { receivedAt?: number } | null;
  telemetrySource: "none" | "synthetic" | "wss";
  onMissionPlanChange: (plan: LocalMissionPlan) => void;
  onEnvironmentChange: (environment: MissionEnvironment) => void;
};
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const clock = () => new Date().toLocaleTimeString("fr-FR", { hour12: false });

function sparkline(values: number[], width = 240, height = 52) {
  if (values.length < 2) return "";
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  return values.map((value, index) => `${index ? "L" : "M"}${(index / (values.length - 1)) * width},${height - 4 - ((value - min) / span) * (height - 10)}`).join(" ");
}
function TelemetryChart({ title, value, unit, values, tone }: { title: string; value: string; unit: string; values: number[]; tone: string }) {
  return <article className="fom-chart-card"><div><span>{title}</span><strong>{value}<small>{unit}</small></strong></div><svg viewBox="0 0 240 52" preserveAspectRatio="none" aria-label={`${title}, historique de télémétrie synthétique`}><path className={`fom-chart-line ${tone}`} d={sparkline(values)} /></svg></article>;
}

export function FlightOperationsModules({ demoState, activeWaypoint, waypoints, missionPlan, environment, enduranceH, batteryWh, telemetryState, telemetry, telemetrySource, onMissionPlanChange, onEnvironmentChange }: Props) {
  const [view, setView] = useState<"telemetry" | "tactical" | "thermal" | "logs" | "mission">("telemetry");
  const [samples, setSamples] = useState<Sample[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([
    { time: clock(), level: "INFO", event: "SIM.SESSION_READY", detail: "Console locale initialisée; sorties physiques désactivées." },
    { time: clock(), level: "SIM", event: "TELEMETRY.SYNTHETIC", detail: "Aucune donnée capteur revendiquée; courbes issues du modèle de démonstration." },
  ]);
  const tick = useRef(0);
  const priorState = useRef(demoState);
  const priorWaypoint = useRef(activeWaypoint);
  const latestTelemetry = useRef(telemetry);
  latestTelemetry.current = telemetry;
  const current = waypoints[activeWaypoint];

  useEffect(() => {
    const timer = window.setInterval(() => {
      tick.current += 1;
      const phase = tick.current / 3;
      const active = demoState === "running";
      const targetSpeed = active ? current?.speedKmh ?? 0 : 0;
      const targetAltitude = active ? current?.altitudeM ?? 0 : 0;
      const batteryPct = clamp(100 - (active ? tick.current / Math.max(1, enduranceH * 36) : 0), 0, 100);
      const frame = latestTelemetry.current;
      const externalFrameFresh = telemetrySource === "wss" && frame?.receivedAt !== undefined && Date.now() - frame.receivedAt < 2500;
      const sample: Sample = {
        t: tick.current,
        speed: externalFrameFresh ? frame?.speedKmh ?? targetSpeed : Math.max(0, targetSpeed + (active ? Math.sin(phase) * 1.2 : 0)),
        altitude: externalFrameFresh ? frame?.altitudeM ?? targetAltitude : Math.max(0, targetAltitude + (active ? Math.sin(phase * 0.7) * 0.7 : 0)),
        pitch: externalFrameFresh ? frame?.pitchDeg ?? 0 : active ? Math.sin(phase * 0.8) * 3.5 : 0,
        roll: externalFrameFresh ? frame?.rollDeg ?? 0 : active ? Math.sin(phase * 0.6) * 2.2 : 0,
        battery: externalFrameFresh ? frame?.batteryPct ?? batteryPct : batteryPct,
      };
      setSamples(previous => [...previous, sample].slice(-28));
    }, 850);
    return () => window.clearInterval(timer);
  }, [demoState, current?.speedKmh, current?.altitudeM, enduranceH, telemetrySource]);

  useEffect(() => {
    if (priorState.current !== demoState) {
      const state = demoState.toUpperCase();
      setLogs(previous => [{ time: clock(), level: (demoState === "running" ? "SIM" : "INFO") as LogEntry["level"], event: `MISSION.STATE_${state}`, detail: `État local mis à jour : ${demoState}.` }, ...previous].slice(0, 18));
      priorState.current = demoState;
    }
  }, [demoState]);
  useEffect(() => {
    if (priorWaypoint.current !== activeWaypoint && waypoints[activeWaypoint]) {
      const point = waypoints[activeWaypoint];
      setLogs(previous => [{ time: clock(), level: "SIM" as const, event: "ROUTE.WAYPOINT_SELECTED", detail: `${point.id} ${point.name} · ${point.altitudeM} m · simulation locale.` }, ...previous].slice(0, 18));
      priorWaypoint.current = activeWaypoint;
    }
  }, [activeWaypoint, waypoints]);

  const latest = samples[samples.length - 1];
  const speedData = useMemo(() => samples.map(item => item.speed), [samples]);
  const altitudeData = useMemo(() => samples.map(item => item.altitude), [samples]);
  const pitchData = useMemo(() => samples.map(item => item.pitch), [samples]);
  const rollData = useMemo(() => samples.map(item => item.roll), [samples]);
  const batteryData = useMemo(() => samples.map(item => item.battery), [samples]);
  const wssFresh = telemetrySource === "wss" && telemetry?.receivedAt !== undefined && Date.now() - telemetry.receivedAt < 2500;
  const coords = [{ x: missionPlan.homeX, y: missionPlan.homeY }, ...waypoints, { x: missionPlan.homeX, y: missionPlan.homeY }];
  const routePath = coords.map(point => `${point.x},${point.y}`).join(" ");
  const stressPenalty = clamp(1 - Math.max(0, environment.windKmh - 8) * 0.004 - Math.abs(environment.ambientC - 20) * 0.002 - environment.emiLevel * 0.06, 0.35, 1);
  const degradedEndurance = enduranceH * stressPenalty;

  const updateWaypoint = (index: number, patch: Partial<MissionWaypoint>) => {
    const next = missionPlan.waypoints.map((point, i) => i === index ? { ...point, ...patch } : point);
    onMissionPlanChange({ ...missionPlan, waypoints: next });
  };
  const addWaypoint = () => {
    const last = waypoints.at(-1) ?? { x: missionPlan.homeX + 8, y: missionPlan.homeY - 8, altitudeM: 60, speedKmh: 35 };
    const point: MissionWaypoint = { id: `WP-${String(Date.now()).slice(-5)}`, name: `Point ${waypoints.length + 1}`, x: clamp(last.x + 10, 5, 95), y: clamp(last.y - 8, 5, 95), altitudeM: last.altitudeM, speedKmh: last.speedKmh, action: "turn" };
    onMissionPlanChange({ ...missionPlan, waypoints: [...waypoints, point] });
  };
  const planDetour = () => {
    const center = { x: 53, y: 51 }, radius = 13;
    let changed = false;
    const next = waypoints.map((point, index) => {
      const distance = Math.hypot(point.x - center.x, point.y - center.y);
      if (distance < radius + 3) {
        changed = true;
        const dx = point.x - center.x, dy = point.y - center.y;
        const length = Math.hypot(dx, dy) || 1;
        return { ...point, x: clamp(center.x + dx / length * (radius + 8), 4, 96), y: clamp(center.y + dy / length * (radius + 8), 4, 96), action: "turn" as const, name: point.name.includes("détour") ? point.name : `${point.name} · détour` };
      }
      if (!changed && index === waypoints.length - 1 && distance >= radius + 3) {
        return point;
      }
      return point;
    });
    if (!changed && next.length) {
      const index = Math.floor(next.length / 2), point = next[index];
      next[index] = { ...point, x: clamp(point.x, 4, 96), y: clamp(point.y - (point.y > center.y ? 18 : -18), 4, 96), action: "turn", name: `${point.name} · détour simulé` };
    }
    onMissionPlanChange({ ...missionPlan, waypoints: next });
    setLogs(previous => [{ time: clock(), level: "SIM" as const, event: "ROUTE.DETOUR_RECALCULATED", detail: "Détour 2D généré autour de la zone d’exclusion illustrée; à vérifier, aucun fond géographique." }, ...previous].slice(0, 18));
  };
  const setEnvironment = (patch: Partial<MissionEnvironment>) => onEnvironmentChange({ ...environment, ...patch });

  const views = [
    ["telemetry", "Télémétrie", Activity], ["tactical", "Carte SIG locale", Map], ["thermal", "Thermique IR", Thermometer], ["logs", "Journal", ClipboardList], ["mission", "Milieux extrêmes", Waypoints],
  ] as const;
  return <section className="fom-shell" aria-label="Modules de simulation tactique">
    <div className="fom-heading"><div><span className="fom-eyebrow">FLIGHT SYSTEMS / SIMULATEUR LOCAL</span><h3>Console de mission &amp; télémétrie</h3></div><span className="fom-synth-badge"><i /> SYNTHÉTIQUE · LECTURE SEULE</span></div>
    <div className="fom-tabs" role="tablist" aria-label="Vues de mission">{views.map(([id, label, Icon]) => <button key={id} role="tab" aria-selected={view === id} className={view === id ? "is-active" : ""} onClick={() => setView(id)}><Icon size={14} />{label}</button>)}</div>

    {view === "telemetry" && <div className="fom-content"><div className="fom-telemetry-meta"><span><Radio size={13} /> {wssFresh ? "Flux WSS reçu · lecture seule" : telemetrySource === "synthetic" ? "Feed synthétique de démonstration" : telemetryState === "connected" ? "WSS connecté · en attente d’une trame" : "Aucun flux · simulation locale"}</span><small>{wssFresh ? "Champs absents : valeur du modèle local; horodatage du frame affiché au journal." : "Courbes de démonstration synthétiques, non mesurées."}</small></div><div className="fom-chart-grid">
      <TelemetryChart title="Vitesse" value={(latest?.speed ?? 0).toFixed(1)} unit="km/h" values={speedData} tone="cyan" />
      <TelemetryChart title="Altitude relative" value={(latest?.altitude ?? 0).toFixed(1)} unit="m" values={altitudeData} tone="blue" />
      <TelemetryChart title="Tangage" value={(latest?.pitch ?? 0).toFixed(1)} unit="°" values={pitchData} tone="violet" />
      <TelemetryChart title="Roulis" value={(latest?.roll ?? 0).toFixed(1)} unit="°" values={rollData} tone="violet" />
      <TelemetryChart title="Batterie" value={`${(latest?.battery ?? 100).toFixed(0)}`} unit="%" values={batteryData} tone="green" />
    </div><div className="fom-kpi-strip"><span>Énergie nominale<strong>{batteryWh} Wh</strong></span><span>État scénario<strong>{demoState.toUpperCase()}</strong></span><span>WP actif<strong>{current?.id ?? "—"}</strong></span></div></div>}

    {view === "tactical" && <div className="fom-content fom-map-layout"><div className="fom-tactical-map"><div className="fom-map-label">CANEVAS LOCAL · COORDONNÉES NORMALISÉES · SANS GPS</div><svg viewBox="0 0 100 100" role="img" aria-label="Carte tactique simulée sans coordonnées géographiques"><defs><pattern id="fom-grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="rgba(117,226,220,.14)" strokeWidth=".35" /></pattern></defs><rect width="100" height="100" fill="url(#fom-grid)"/><circle cx="53" cy="51" r="13" className="fom-no-go-zone"/><text x="53" y="51" textAnchor="middle" className="fom-zone-label">ZONE D’EXCLUSION</text><polyline points={routePath} className="fom-route"/><circle cx={missionPlan.homeX} cy={missionPlan.homeY} r="3.5" className="fom-home"/><text x={missionPlan.homeX + 4} y={missionPlan.homeY + 2} className="fom-map-tag">BASE SIM.</text>{waypoints.map((point, index) => <g key={point.id}><circle cx={point.x} cy={point.y} r={index === activeWaypoint ? 3.6 : 2.4} className={`fom-waypoint ${index === activeWaypoint ? "is-active" : ""}`} /><text x={point.x + 3} y={point.y - 2} className="fom-map-tag">{String(index + 1).padStart(2, "0")}</text></g>)}</svg></div><div className="fom-map-side"><strong>Plan local — {waypoints.length} waypoint(s)</strong><p>La représentation est une carte de canevas sans géoréférencement. La zone hachurée est un obstacle fictif pour tester le calcul de détour.</p><button onClick={planDetour} disabled={!waypoints.length}><Waypoints size={14} /> Calculer un détour simulé</button><small>Revue humaine obligatoire avant toute utilisation hors simulation.</small></div></div>}

    {view === "thermal" && <div className="fom-content"><div className="fom-ir-banner"><Thermometer size={14} /> VUE THERMIQUE SYNTHÉTIQUE · NE PROVIENT PAS D’UN CAPTEUR IR</div><div className="fom-ir-screen" role="img" aria-label="Image thermique illustratrice générée par CSS, sans donnée de capteur"><div className="fom-ir-grid"/><div className="fom-ir-heat heat-a"/><div className="fom-ir-heat heat-b"/><div className="fom-ir-heat heat-c"/><div className="fom-ir-reticle"/><span className="fom-ir-corner">SIM · 25.0°C</span><span className="fom-ir-scale">38°C ━━━ 20°C ━━━ 5°C</span></div><p className="fom-muted-note">Filtre thermique décoratif CSS sur scène virtuelle. Aucun flux vidéo n’est modifié et aucune température réelle n’est mesurée.</p></div>}

    {view === "logs" && <div className="fom-content"><div className="fom-log-head"><strong><ClipboardList size={14} /> Journal structuré de simulation</strong><button onClick={() => setLogs([{ time: clock(), level: "INFO", event: "LOG.CLEARED", detail: "Journal local réinitialisé." }])}>Effacer le journal</button></div><div className="fom-log-table" role="table" aria-label="Journal structuré local"><div className="fom-log-row fom-log-header" role="row"><span>HEURE</span><span>NIVEAU</span><span>ÉVÉNEMENT</span><span>DÉTAIL</span></div>{logs.map((entry, index) => <div className="fom-log-row" role="row" key={`${entry.time}-${entry.event}-${index}`}><span>{entry.time}</span><b className={`level-${entry.level.toLowerCase()}`}>{entry.level}</b><code>{entry.event}</code><span>{entry.detail}</span></div>)}</div></div>}

    {view === "mission" && <div className="fom-content fom-mission-grid"><div className="fom-environment"><div className="fom-panel-title"><AlertTriangle size={15} /> Conditions dégradées (modèle exploratoire)</div><label>Température ambiante <strong>{environment.ambientC} °C</strong><input type="range" min="-20" max="55" step="1" value={environment.ambientC} onChange={event => setEnvironment({ ambientC: Number(event.target.value) })} /></label><label>Vent simulé <strong>{environment.windKmh} km/h</strong><input type="range" min="0" max="70" step="1" value={environment.windKmh} onChange={event => setEnvironment({ windKmh: Number(event.target.value) })} /></label><label>Perturbation CEM <strong>{Math.round(environment.emiLevel * 100)} %</strong><input type="range" min="0" max="1" step="0.05" value={environment.emiLevel} onChange={event => setEnvironment({ emiLevel: Number(event.target.value) })} /></label><div className="fom-degraded-readout"><span>Autonomie de référence<strong>{enduranceH.toFixed(2)} h</strong></span><span>Estimation dégradée<strong>{degradedEndurance.toFixed(2)} h</strong></span><small>Facteur heuristique exploratoire — non qualifié, non utilisable pour autoriser un vol.</small></div></div><div className="fom-waypoint-editor"><div className="fom-panel-title"><Waypoints size={15} /> Éditeur de route canevas <button onClick={addWaypoint}>+ Point</button></div>{waypoints.length ? waypoints.map((point, index) => <div className="fom-waypoint-edit-row" key={point.id}><span>{point.id}</span><input aria-label={`Nom du point ${index + 1}`} value={point.name} onChange={event => updateWaypoint(index, { name: event.target.value })} /><label>Alt. m<input type="number" min="0" max="300" value={point.altitudeM} onChange={event => updateWaypoint(index, { altitudeM: clamp(Number(event.target.value), 0, 300) })} /></label><label>Vitesse<input type="number" min="0" max="150" value={point.speedKmh} onChange={event => updateWaypoint(index, { speedKmh: clamp(Number(event.target.value), 0, 150) })} /></label><button aria-label={`Supprimer ${point.id}`} onClick={() => onMissionPlanChange({ ...missionPlan, waypoints: waypoints.filter((_, i) => i !== index) })}>×</button></div>) : <p className="fom-muted-note">Aucun waypoint. Ajoutez un point pour construire une route de démonstration locale.</p>}<small>Les modifications réinitialisent l’approbation prévol. Pas de coordonnées GPS ni de téléversement de plan.</small></div></div>}
    <div className="fom-safety-note"><AlertTriangle size={13} /> Simulation de recherche, secours et formation uniquement. Les zones et conditions ne décrivent pas un site réel; commandes d’actionneur, largage réel et téléversement sont absents.</div>
  </section>;
}
