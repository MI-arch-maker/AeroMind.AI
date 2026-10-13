from pathlib import Path

root = Path('/home/ubuntu/work/aeromind-inspect/frontend/client/src')

# Extend model unions and 3D fixed-wing handling.
p = root / 'lib/aeroEngine.ts'
s = p.read_text()
s = s.replace('  | "male-voilure";\n', '  | "male-voilure"\n  | "stealth-wing";\n')
p.write_text(s)

p = root / 'lib/droneCatalog.ts'
s = p.read_text()
s = s.replace('  | "male-voilure";\n', '  | "male-voilure"\n  | "stealth-wing";\n')
needle = '  profile({ key: "fixed-wing", modelType: "planeur", id: "glider-01", label: "GLIDER-01", family: "Planeur instrumenté", mission: "Endurance silencieuse, thermiques simulés et relais de mesure scientifique.", specs: "5,8 m · 0,8 kg utile · 1 moteur", disciplines: "Finesse · ballast · thermiques", tone: "cyan", silhouette: "long", configuration: { wingspan: 5.8, chord: 0.26, fuselageLength: 1.8, propDiameter: 0.3, batteryWh: 720, payloadKg: 0.8, cruiseSpeedKmh: 46, motorCount: 1, altitudeM: 220 } }),\n'
addition = needle + '''  profile({ key: "fixed-wing", modelType: "hale-voilure", id: "hale-stratospheric", label: "HALE-STRATOSPHERIC", family: "Profil HALE-Stratospheric", mission: "Surveillance haute altitude non armée et observation de zones de crise environnementale.", specs: "4,8 m · nez bulbeux · 1 moteur", disciplines: "Haute altitude · environnement · endurance", tone: "cyan", silhouette: "long", configuration: { wingspan: 4.8, chord: 0.34, fuselageLength: 2.2, propDiameter: 0.34, batteryWh: 2480, payloadKg: 1.4, cruiseSpeedKmh: 72, motorCount: 1, altitudeM: 18000 } }),
  profile({ key: "fixed-wing", modelType: "male-voilure", id: "male-longenver", label: "MALE-LONGENVER", family: "Profil MALE-LongEnver", mission: "Inspection de sécurité civile sur corridors étendus, avec grande autonomie et capteurs non offensifs.", specs: "3,6 m · fuselage 2,1 m · 1 moteur", disciplines: "Corridor · V inversé · autonomie", tone: "amber", silhouette: "long", configuration: { wingspan: 3.6, chord: 0.38, fuselageLength: 2.1, propDiameter: 0.38, batteryWh: 2120, payloadKg: 1.8, cruiseSpeedKmh: 68, motorCount: 1, altitudeM: 9000 } }),
  profile({ key: "fixed-wing", modelType: "stealth-wing", id: "stealth-wing-01", label: "STEALTH-WING", family: "Profil Furtif Stealth-Wing", mission: "Aile volante intégrée pour collecte de capteurs en environnement électromagnétique perturbé, sans charge offensive.", specs: "3,2 m · aile volante intégrée · 1 moteur", disciplines: "Faible signature · CEM · aile volante", tone: "violet", silhouette: "flat", configuration: { wingspan: 3.2, chord: 0.52, fuselageLength: 1.35, propDiameter: 0.3, batteryWh: 1860, payloadKg: 1.1, cruiseSpeedKmh: 84, motorCount: 1, altitudeM: 6000 } }),
'''
if needle not in s:
    raise SystemExit('catalog anchor not found')
s = s.replace(needle, addition, 1)
p.write_text(s)

p = root / 'components/PhysicalDroneModel.tsx'
s = p.read_text()
s = s.replace('"hale-voilure", "male-voilure"].includes(modelType)', '"hale-voilure", "male-voilure", "stealth-wing"].includes(modelType)')
s = s.replace('"hale-voilure", "male-voilure"].includes(design?.modelType ?? "")', '"hale-voilure", "male-voilure", "stealth-wing"].includes(design?.modelType ?? "")')
s = s.replace('  interactive?: boolean;\n};', '  interactive?: boolean;\n  showGrid?: boolean;\n};', 1)
s = s.replace('function Scene({ design, status, flightState, parts, interactive }: PhysicalDroneModelProps & { interactive: boolean }) {', 'function Scene({ design, status, flightState, parts, interactive, showGrid }: PhysicalDroneModelProps & { interactive: boolean }) {')
s = s.replace('    <ambientLight intensity={0.75} />', '    {showGrid && <gridHelper args={[8, 32, "#00e5ff", "#123a43"]} position={[0, -0.72, 0]} />}\n    {showGrid && <axesHelper args={[2.8]} position={[0, -0.7, 0]} />}\n    <ambientLight intensity={0.75} />')
s = s.replace('export function PhysicalDroneModel({ design, status = "idle", compact = false, construction, parts = [], flightState, interactive = true }: PhysicalDroneModelProps) {', 'export function PhysicalDroneModel({ design, status = "idle", compact = false, construction, parts = [], flightState, interactive = true, showGrid = false }: PhysicalDroneModelProps) {')
s = s.replace('<Scene design={design} status={status} flightState={flightState} parts={parts} interactive={interactive} />', '<Scene design={design} status={status} flightState={flightState} parts={parts} interactive={interactive} showGrid={showGrid} />')
p.write_text(s)

# Replace inspector's legacy SVG canvas call with persistent parametric WebGL model.
p = root / 'pages/Home.tsx'
s = p.read_text()
if 'import { PhysicalDroneModel }' not in s:
    s = s.replace('import { ParametricDronePreview } from "../components/ParametricDronePreview";\n', 'import { ParametricDronePreview } from "../components/ParametricDronePreview";\nimport { PhysicalDroneModel } from "../components/PhysicalDroneModel";\n')
old = '''          <ConceptCanvas
            config={config}
            selected={selectedComponent}
            onSelect={setSelectedComponent}
            rotation={rotation}
            rotationX={rotationX}
            rotationY={rotationY}
            zoom={zoom}
            setRotation={setRotation}
            setRotationX={setRotationX}
            setRotationY={setRotationY}
            setZoom={setZoom}
          />'''
new = '''          <div className="inspector-live-3d-stage">
            <PhysicalDroneModel
              design={(droneCatalog.find(item => item.id === config.platformProfile) ?? droneCatalog[0]) && {
                ...(droneCatalog.find(item => item.id === config.platformProfile) ?? droneCatalog[0]),
                configuration: { ...(droneCatalog.find(item => item.id === config.platformProfile) ?? droneCatalog[0]).configuration, ...config },
              }}
              construction={{ parts: config.installedMaterials?.length ?? 0, massKg: config.constructionMassKg ?? 0 }}
              interactive
              showGrid
            />
            <div className="inspector-live-3d-readout">
              <span>WEBGL / GRILLE ACTIVE</span>
              <b>{config.wingspan.toFixed(2)} m · {config.fuselageLength.toFixed(2)} m · {config.payloadKg.toFixed(2)} kg utile</b>
              <small>Masse {config.constructionMassKg?.toFixed(2) ?? "0.00"} kg · vent {config.windSpeedKmh} km/h · recalcul en direct</small>
            </div>
          </div>'''
if old not in s:
    raise SystemExit('inspector canvas anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

# Use the persistent 3D construction view with a Three.js grid.
p = root / 'components/DesignStudioView.tsx'
s = p.read_text()
s = s.replace('                interactive\n              />', '                interactive\n                showGrid\n              />', 1)
p.write_text(s)

# Add dynamic compliance bars to the requirements screen.
p = root / 'pages/Home.tsx'
s = p.read_text()
anchor = '''      <EngineeringGuide
        eyebrow="CONSOLE INGÉNIEUR / EXIGENCES"'''
insert = '''      <section className="requirements-compliance-panel panel" aria-label="Conformité dynamique des profils de mission">
        <div className="requirements-compliance-heading">
          <div><p className="eyebrow">CONFORMITÉ DYNAMIQUE</p><h3>Profils de mission</h3></div>
          <span>{requirements.length ? `${Math.round((requirements.filter(item => item.approved || item.status === "ok").length / requirements.length) * 100)}% suivi` : "0% suivi"}</span>
        </div>
        {[{ label: "Recherche & secours civils", key: "rescue" }, { label: "Inspection", key: "inspection" }].map(profile => {
          const base = profile.key === "rescue" ? requirements.filter(item => /secours|sauvetage|balise|retour/i.test(`${item.label} ${item.description ?? ""}`)) : requirements.filter(item => /inspection|structure|corridor|capteur/i.test(`${item.label} ${item.description ?? ""}`));
          const pool = base.length ? base : requirements;
          const complete = pool.filter(item => item.approved || item.status === "ok").length;
          const percent = pool.length ? Math.round((complete / pool.length) * 100) : 0;
          return <div className="requirements-compliance-row" key={profile.key}><div><strong>{profile.label}</strong><small>{complete}/{pool.length || 0} critères vérifiés</small></div><div className="requirements-progress-track"><span style={{ width: `${percent}%` }} /></div><b>{percent}%</b></div>;
        })}
      </section>
'''
if anchor not in s:
    raise SystemExit('requirements anchor not found')
s = s.replace(anchor, insert + anchor, 1)
p.write_text(s)

# Add premium cyber theme overrides without disrupting legacy tokens.
p = root / 'aeromind-dynamics.css'
s = p.read_text()
s += '''\n\n/* Premium Dark Cyber workspace layer */\n:root { --cyber-green: #00ff66; --cyber-amber: #ffb300; --cyber-cyan: #00e5ff; }\n.inspector-live-3d-stage { position: relative; min-height: 500px; overflow: hidden; border: 1px solid rgba(0,229,255,.28); background: radial-gradient(circle at 50% 35%, rgba(0,229,255,.12), transparent 54%), #030b10; }\n.inspector-live-3d-stage .physical-drone-stage { min-height: 500px; border: 0; border-radius: 0; background: transparent; }\n.inspector-live-3d-readout { position: absolute; left: 14px; right: 14px; bottom: 12px; display: grid; gap: 3px; padding: 10px 12px; color: #a8f6ff; background: rgba(2,12,16,.8); border: 1px solid rgba(0,229,255,.26); font: 10px/1.3 ui-monospace, monospace; letter-spacing: .08em; pointer-events: none; }\n.inspector-live-3d-readout b { color: var(--cyber-green); }\n.inspector-live-3d-readout small { color: #8ba7ad; letter-spacing: .02em; }\n.requirements-compliance-panel { display: grid; gap: 14px; border-color: rgba(0,229,255,.24); background: linear-gradient(135deg, rgba(0,229,255,.055), rgba(0,255,102,.025)); }\n.requirements-compliance-heading, .requirements-compliance-row { display: flex; align-items: center; gap: 14px; }\n.requirements-compliance-heading { justify-content: space-between; }\n.requirements-compliance-heading h3 { margin: 2px 0 0; }\n.requirements-compliance-heading > span { color: var(--cyber-green); font: 700 12px ui-monospace, monospace; }\n.requirements-compliance-row > div:first-child { display: grid; gap: 3px; min-width: 190px; }\n.requirements-compliance-row small { color: #78949b; }\n.requirements-progress-track { flex: 1; height: 8px; overflow: hidden; background: rgba(255,255,255,.08); border: 1px solid rgba(0,229,255,.16); }\n.requirements-progress-track span { display: block; height: 100%; background: linear-gradient(90deg, var(--cyber-cyan), var(--cyber-green)); box-shadow: 0 0 12px rgba(0,255,102,.5); transition: width .35s ease; }\n.requirements-compliance-row > b { min-width: 42px; color: var(--cyber-amber); text-align: right; font-family: ui-monospace, monospace; }\n@media (max-width: 720px) { .requirements-compliance-row { align-items: stretch; flex-direction: column; gap: 6px; } .requirements-compliance-row > div:first-child { min-width: 0; } }\n'''
p.write_text(s)
PY
python3 /home/ubuntu/work/aeromind-inspect/tools/apply_second_roadmap.py
rm /home/ubuntu/work/aeromind-inspect/tools/apply_second_roadmap.py
