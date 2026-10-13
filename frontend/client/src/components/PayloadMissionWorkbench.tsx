import { useEffect, useState } from "react";
import { Camera, CheckCircle2, Crosshair, PackageCheck, Play, ScanLine, ShieldCheck } from "lucide-react";
import type { InstalledMaterial } from "../lib/aeroEngine";
import "./payload-workbench.css";

type Props = { installed: InstalledMaterial[]; onInstall: (id: string) => void };
const modules = [
  { id: "camera-rgb", label: "Caméra optronique RGB", type: "Imagerie visible", mass: "0,12 kg", icon: Camera },
  { id: "thermal-camera", label: "Capteur thermique IR", type: "Thermographie synthétique", mass: "0,16 kg", icon: ScanLine },
  { id: "lidar-unit", label: "Capteur LiDAR", type: "Nuage de points simulé", mass: "0,28 kg", icon: Crosshair },
  { id: "rescue-package", label: "Module colis de secours", type: "Séquence de mission au sol", mass: "0,24 kg", icon: PackageCheck },
];
const phases = [
  "Vérification des interfaces logicielles",
  "Calibration virtuelle du capteur",
  "Prévisualisation de séquence",
  "Fin du test — aucune sortie physique",
];

export function PayloadMissionWorkbench({ installed, onInstall }: Props) {
  const [selectedId, setSelectedId] = useState("camera-rgb");
  const [gimbalPitch, setGimbalPitch] = useState(0);
  const [fieldOfView, setFieldOfView] = useState(62);
  const [phase, setPhase] = useState(-1);
  const [running, setRunning] = useState(false);
  const selected = modules.find(item => item.id === selectedId) ?? modules[0];
  const isInstalled = installed.some(item => item.id.startsWith(selectedId));

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setPhase(current => {
      if (current >= phases.length - 1) { setRunning(false); return current; }
      return current + 1;
    }), 900);
    return () => window.clearInterval(timer);
  }, [running]);

  const runSequence = () => { setPhase(0); setRunning(true); };
  return (
    <section className="payload-workbench panel" aria-label="Atelier virtuel des modules de mission">
      <div className="payload-workbench-heading">
        <div>
          <p className="eyebrow">PAYLOAD INTEGRATION / SOL SIMULATOR</p>
          <h3>Atelier équipements &amp; calibration</h3>
          <small>Modules de recherche, inspection et secours civil; les essais restent virtuels.</small>
        </div>
        <span><ShieldCheck size={13} /> PAS DE SORTIE MATÉRIELLE</span>
      </div>
      <div className="payload-workbench-grid">
        <div className="payload-module-picker">
          {modules.map(item => {
            const Icon = item.icon;
            const itemInstalled = installed.some(part => part.id.startsWith(item.id));
            return (
              <button key={item.id} className={selectedId === item.id ? "is-active" : ""} onClick={() => setSelectedId(item.id)}>
                <Icon size={16} />
                <span><strong>{item.label}</strong><small>{item.type} · {item.mass}</small></span>
                {itemInstalled && <CheckCircle2 size={14} className="payload-installed" />}
              </button>
            );
          })}
        </div>
        <div className="payload-calibration">
          <div className="payload-calibration-top"><strong>{selected.label}</strong><small>{isInstalled ? "INSTALLÉ AU MODÈLE" : "RÉFÉRENCE NON INSTALLÉE"}</small></div>
          <label>Inclinaison nacelle <b>{gimbalPitch}°</b><input type="range" min="-45" max="45" step="1" value={gimbalPitch} onChange={event => setGimbalPitch(Number(event.target.value))} /></label>
          <label>Champ de vision simulé <b>{fieldOfView}°</b><input type="range" min="20" max="120" step="1" value={fieldOfView} onChange={event => setFieldOfView(Number(event.target.value))} /></label>
          <div className="payload-preview"><span className="payload-reticle" /><small>APERÇU LOGICIEL · {selected.type.toUpperCase()}</small></div>
          <div className="payload-actions">
            <button onClick={() => onInstall(selected.id)} disabled={isInstalled}>+ {isInstalled ? "Déjà installé" : "Installer dans le modèle"}</button>
            <button className="payload-test-button" onClick={runSequence} disabled={running}><Play size={13} />{running ? "Test en cours…" : selected.id === "rescue-package" ? "Tester le déploiement simulé" : "Lancer calibration simulée"}</button>
          </div>
          <div className="payload-sequence" aria-live="polite">
            <span>SÉQUENCE DE TEST</span>
            {phase < 0 ? <small>Prête · aucune activation physique n’est possible.</small> : <small className={phase === phases.length - 1 && !running ? "is-complete" : ""}>{String(phase + 1).padStart(2, "0")} / {phases.length} · {phases[phase]}</small>}
          </div>
        </div>
      </div>
      <p className="payload-boundary"><ShieldCheck size={13} /> « Activer » signifie uniquement démarrer une séquence logicielle locale. Ce banc n’arme aucun mécanisme, ne largue aucun colis et ne contrôle aucun capteur connecté.</p>
    </section>
  );
}
