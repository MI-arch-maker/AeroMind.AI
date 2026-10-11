import React, { useEffect, useState } from 'react'
import { get, post } from '../api.js'
import { LineChart } from '../ui.jsx'

export default function Propulsion() {
  const [sources, setSources] = useState({})
  const [sel, setSel] = useState(['lipo', 'h2_fc', 'gas_4t'])
  const [f, setF] = useState({ mtom_kg: 7, n_props: 4, prop_d_m: 0.33, payload_kg: 1,
    energy_kg: 1, mode: 'hover', v_cruise: 20, ld: 10, t_max_h: 2 })
  const [res, setRes] = useState(null)
  const [curve, setCurve] = useState(null)
  const [tReq, setTReq] = useState(1)
  useEffect(() => { get('/api/propulsion/sources').then(setSources) }, [])
  const run = async () => {
    setRes(await post('/api/propulsion/compare', { ...f, sources: sel }))
    setCurve(await post('/api/propulsion/payload-curve', { ...f, sources: sel, n_points: 25 }))
  }
  return (
    <>
      <h1>Propulsion — élec / hydrogène / thermique</h1>
      <div className="card">
        <div className="grid">
          <div><label>MTOM (kg)</label><input type="number" step="0.1" value={f.mtom_kg} onChange={e => setF({ ...f, mtom_kg: +e.target.value })} /></div>
          <div><label>Nombre d'hélices</label><input type="number" value={f.n_props} onChange={e => setF({ ...f, n_props: +e.target.value })} /></div>
          <div><label>Diamètre hélice (m)</label><input type="number" step="0.01" value={f.prop_d_m} onChange={e => setF({ ...f, prop_d_m: +e.target.value })} /></div>
          <div><label>Masse d'énergie (kg)</label><input type="number" step="0.1" value={f.energy_kg} onChange={e => setF({ ...f, energy_kg: +e.target.value })} /></div>
          <div><label>Mode</label><select value={f.mode} onChange={e => setF({ ...f, mode: e.target.value })}>
            <option value="hover">Stationnaire (multirotor)</option><option value="cruise">Croisière (voilure fixe)</option></select></div>
          <div><label>V croisière (m/s)</label><input type="number" value={f.v_cruise} onChange={e => setF({ ...f, v_cruise: +e.target.value })} /></div>
          <div><label>Finesse L/D</label><input type="number" value={f.ld} onChange={e => setF({ ...f, ld: +e.target.value })} /></div>
          <div><label>Endurance max courbe (h)</label><input type="number" step="0.5" value={f.t_max_h} onChange={e => setF({ ...f, t_max_h: +e.target.value })} /></div>
        </div>
        <div className="row sm" style={{ margin: '8px 0' }}>
          {Object.entries(sources).map(([k, s]) => (
            <label key={k} style={{ display: 'flex', gap: 6, alignItems: 'center', margin: 0 }}>
              <input type="checkbox" style={{ width: 'auto' }} checked={sel.includes(k)}
                onChange={e => setSel(e.target.checked ? [...sel, k] : sel.filter(x => x !== k))} />
              <span style={{ color: s.color }}>{s.label}</span></label>))}
        </div>
        <button className="p" onClick={run}>Comparer</button>
      </div>
      {res && <>
        <div className="card">
          <h3>Puissance requise : {res.power_w} W ({res.mode === 'hover' ? 'stationnaire' : 'croisière'})</h3>
          <table>
            <thead><tr><th>Source</th><th>Énergie utile</th><th>Endurance</th><th>Autonomie</th></tr></thead>
            <tbody>{res.results.map(r => (
              <tr key={r.key}><td style={{ color: r.color }}>{r.label}</td>
                <td>{r.usable_wh} Wh ({r.energy_kg} kg)</td><td>{r.endurance_h} h</td>
                <td>{r.range_km !== null ? r.range_km + ' km' : '—'}</td></tr>))}</tbody>
          </table>
        </div>
        <div className="grid">
          <div className="card"><h3>Charge utile vs endurance</h3>
            {curve && <LineChart series={curve.series} xLabel="endurance (h)" yLabel="charge utile (kg)" />}</div>
          <div className="card"><h3>Masse d'énergie requise pour {tReq} h</h3>
            <input type="range" min="0.2" max={f.t_max_h} step="0.1" value={tReq} onChange={e => setTReq(+e.target.value)} />
            {res.results.map(r => {
              const mE = res.power_w * tReq / (r.wh_per_kg * r.eff)
              return <div key={r.key} style={{ margin: '8px 0' }}>
                <div className="sm" style={{ color: r.color }}>{r.label} — {mE.toFixed(2)} kg
                  ({Math.min(100, mE / res.budget.mtom_kg * 100).toFixed(0)}% du MTOM)</div>
                <div className="bar"><i style={{ width: `${Math.min(100, mE / res.budget.mtom_kg * 100)}%`, background: r.color }} /></div>
              </div>})}
            <p className="sm mut" style={{ marginTop: 10 }}>Budget : structure {res.budget.structure_kg} kg +
                fixes {res.budget.fixed_kg} kg + charge utile {res.budget.payload_kg} kg + énergie ≤ {res.budget.mtom_kg} kg</p>
          </div>
        </div>
      </>}
    </>
  )
}