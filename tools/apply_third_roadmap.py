from pathlib import Path

root=Path('/home/ubuntu/work/aeromind-inspect/frontend/client/src')

p=root/'components/PhysicalDroneModel.tsx'
s=p.read_text()
s=s.replace('  interactive?: boolean;\n};','  interactive?: boolean;\n  showGrid?: boolean;\n};',1)
s=s.replace('"hale-voilure", "male-voilure"].includes(modelType)', '"hale-voilure", "male-voilure", "stealth-wing"].includes(modelType)')
s=s.replace('"hale-voilure", "male-voilure"].includes(design?.modelType ?? "")', '"hale-voilure", "male-voilure", "stealth-wing"].includes(design?.modelType ?? "")')
# Insert specialized meshes before DroneMesh.
marker='function DroneMesh({ design, status, flightState, parts = [] }: Pick<PhysicalDroneModelProps, "design" | "status" | "flightState" | "parts">) {'
insert=r'''function ExtendedAeroMesh({ material }: { material: THREE.Material }) {
  return <group rotation={[0, 0, Math.PI / 2]}>
    <mesh castShadow material={material}><cylinderGeometry args={[0.12, 0.19, 2.15, 20]} /></mesh>
    <mesh position={[0, 0.96, 0]} rotation={[0, 0, Math.PI / 2]} castShadow material={material}><coneGeometry args={[0.23, 0.34, 24]} /></mesh>
    <mesh position={[0, -0.63, 0]} rotation={[0, 0, Math.PI / 2]} castShadow material={material}><boxGeometry args={[0.08, 1.42, 0.05]} /></mesh>
    <mesh position={[0, -0.78, 0.18]} rotation={[0.3, 0, 0]} castShadow material={material}><boxGeometry args={[0.06, 0.52, 0.055]} /></mesh>
    <mesh position={[0, -0.78, -0.18]} rotation={[-0.3, 0, 0]} castShadow material={material}><boxGeometry args={[0.06, 0.52, 0.055]} /></mesh>
    <mesh position={[0, -0.18, 0]} rotation={[0, 0, Math.PI / 2]} castShadow material={material}><boxGeometry args={[0.055, 2.4, 0.035]} /></mesh>
  </group>;
}
function ProfiledAeroMesh({ material }: { material: THREE.Material }) {
  return <group rotation={[0, 0, Math.PI / 2]}>
    <mesh castShadow material={material}><capsuleGeometry args={[0.18, 1.45, 10, 24]} /></mesh>
    <mesh position={[0, 0.85, 0]} castShadow material={material}><sphereGeometry args={[0.28, 24, 16]} /></mesh>
    <mesh position={[0, -0.1, 0]} rotation={[0, 0, Math.PI / 2]} castShadow material={material}><boxGeometry args={[0.08, 1.85, 0.045]} /></mesh>
    <mesh position={[0, -0.75, 0.16]} rotation={[0.34, 0, 0]} castShadow material={material}><boxGeometry args={[0.055, 0.42, 0.045]} /></mesh>
    <mesh position={[0, -0.75, -0.16]} rotation={[-0.34, 0, 0]} castShadow material={material}><boxGeometry args={[0.055, 0.42, 0.045]} /></mesh>
  </group>;
}
function StealthWingMesh({ material }: { material: THREE.Material }) {
  const shape = useMemo(() => { const sh = new THREE.Shape(); sh.moveTo(-1.55, 0); sh.lineTo(0.95, 0.55); sh.lineTo(1.35, 0); sh.lineTo(0.95, -0.55); sh.closePath(); return sh; }, []);
  return <group rotation={[0, 0, Math.PI / 2]}>
    <mesh castShadow material={material}><extrudeGeometry args={[shape, { depth: 0.11, bevelEnabled: true, bevelSegments: 2, bevelSize: 0.025, bevelThickness: 0.025 }]} /></mesh>
    <mesh position={[0.15, 0, 0.11]} castShadow><boxGeometry args={[0.42, 0.12, 0.12]} /><meshStandardMaterial color="#101c24" metalness={0.7} roughness={0.26} /></mesh>
  </group>;
}
'''
if marker not in s: raise SystemExit('DroneMesh marker not found')
s=s.replace(marker,insert+'\n'+marker,1)
# Specialized branch at beginning of DroneMesh return.
old='''  return <group ref={root}>
    <mesh castShadow receiveShadow material={frameMaterial} scale={[1, 0.78, 0.42]}><capsuleGeometry args={[0.22, 1.35, 8, 20]} /></mesh>
    {fixedWing ? <>'''
new='''  const specialized = modelType === "hale-voilure" || modelType === "male-voilure" || modelType === "stealth-wing";
  return <group ref={root}>
    {specialized ? (modelType === "stealth-wing" ? <StealthWingMesh material={frameMaterial} /> : modelType === "hale-voilure" ? <ExtendedAeroMesh material={frameMaterial} /> : <ProfiledAeroMesh material={frameMaterial} />) : <>
      <mesh castShadow receiveShadow material={frameMaterial} scale={[1, 0.78, 0.42]}><capsuleGeometry args={[0.22, 1.35, 8, 20]} /></mesh>
    {fixedWing ? <>'''
if old not in s: raise SystemExit('DroneMesh return marker not found')
s=s.replace(old,new,1)
# Close fragment just before nose mesh.
s=s.replace('''    </>}
    <mesh position={[0, -0.02, 0.3]}''','''    </>}
    </>}
    <mesh position={[0, -0.02, 0.3]}''',1)
# Scene grid and prop plumbing.
s=s.replace('function Scene({ design, status, flightState, parts, interactive }: PhysicalDroneModelProps & { interactive: boolean }) {','function Scene({ design, status, flightState, parts, interactive, showGrid }: PhysicalDroneModelProps & { interactive: boolean }) {')
s=s.replace('''    <ambientLight intensity={0.75} />''','''    {showGrid && <gridHelper args={[8, 32, "#00e5ff", "#123a43"]} position={[0, -0.72, 0]} />}
    {showGrid && <axesHelper args={[2.8]} position={[0, -0.70, 0]} />}
    <ambientLight intensity={0.75} />''',1)
s=s.replace('export function PhysicalDroneModel({ design, status = "idle", compact = false, construction, parts = [], flightState, interactive = true }: PhysicalDroneModelProps) {','export function PhysicalDroneModel({ design, status = "idle", compact = false, construction, parts = [], flightState, interactive = true, showGrid = false }: PhysicalDroneModelProps) {')
s=s.replace('<Scene design={design} status={status} parts={parts} flightState={flightState} interactive={interactive} />','<Scene design={design} status={status} parts={parts} flightState={flightState} interactive={interactive} showGrid={showGrid} />')
p.write_text(s)

# Use the real 3D preview for the three advanced profiles in the catalogue.
p=root/'pages/Home.tsx'; s=p.read_text()
old='''            <div className="catalog-visual">
              <ParametricDronePreview design={item} />
            </div>'''
new='''            <div className="catalog-visual catalog-visual-overlay">
              {(["hale-voilure", "male-voilure", "stealth-wing"] as string[]).includes(item.modelType ?? "") ? (
                <PhysicalDroneModel design={item} compact status="flying" interactive={false} />
              ) : <ParametricDronePreview design={item} />}
            </div>'''
if old not in s: raise SystemExit('catalog visual marker not found')
s=s.replace(old,new,1)
p.write_text(s)

# Apply construction 3D grid to DesignStudio call if absent.
p=root/'components/DesignStudioView.tsx'; s=p.read_text()
if 'interactive\n                showGrid' not in s:
    s=s.replace('''                interactive
              />''','''                interactive
                showGrid
              />''',1)
p.write_text(s)

# Fluid overlay treatment for catalogue and specialized cards.
p=root/'aeromind-dynamics.css'; s=p.read_text()
s += '''\n\n/* Catalogue 3D overlay / fluid grid */\n.catalog-grid { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; align-items: stretch; }\n.catalog-card { position: relative; overflow: visible; background: linear-gradient(145deg, rgba(0,229,255,.045), rgba(0,255,102,.018)); border-color: rgba(0,229,255,.22); box-shadow: 0 0 22px rgba(0,229,255,.04); }\n.catalog-card:hover { z-index: 2; transform: translateY(-2px); box-shadow: 0 0 30px rgba(0,229,255,.13); }\n.catalog-visual-overlay { min-height: 190px; background: radial-gradient(circle at 50% 50%, rgba(0,229,255,.18), transparent 65%), rgba(2,12,16,.74); }\n.catalog-visual-overlay .physical-drone-stage { min-height: 190px; border: 0; background: transparent; }\n.catalog-visual-overlay .physical-drone-canvas { min-height: 190px; }\n.catalog-visual-overlay .physical-drone-caption { display: none; }\n.catalog-visual-overlay .physical-drone-stage-3d::after { content: "LIVE PARAMETRIC MESH"; position: absolute; left: 10px; top: 9px; color: #00ff66; font: 9px ui-monospace, monospace; letter-spacing: .12em; pointer-events: none; }\n@media (max-width: 720px) { .catalog-grid { grid-template-columns: 1fr; } }\n'''
p.write_text(s)
