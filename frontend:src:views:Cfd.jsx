import React, { useEffect, useState } from 'react'
import { get, post } from '../api.js'
import { LineChart } from '../ui.jsx'

export default function Cfd() {
  const [caps, setCaps] = useState({})
  const [f, setF] = useState({ code: '2412', alpha_min: -6, alpha_max: 16, step: 1, re: 1e6, ar: '', alpha_deg: 4 })
  const [sweep, setSweep] = useState(null)
  const [single, setSingle] = useState(null)
  const [glance, setGlance] = useState(null)
  const [msg, setMsg] = useState('')
  useEffect(() => { get('/api/cfd/capabilities').then(setCaps).catch(e => setMsg(e.message)) }, [])
  const body = { ...f, ar: f.ar || null }
  return (
    <>
      <h1>CFD — profil NACA 4 chiffres</h1>
      <p className="sm mut">
        Solveur : <b>méthode de panneaux Hess–Smith</b> (sources + tourbillon, condition de Kutta)
        {caps.openfoam ? ' + <b>OpenFOAM RANS disponible</b>' : ' — OpenFOAM RANS non déployé (voir Dockerfile.openfoam)'}
      </p>
      <div className="card">
        <div className="grid">
          <div><label>Profil (NACA)</label><input value={f.code} onChange={e => setF({ ...f, code: e.target.value })} /></div>
          <div><label>α min (°)</label><input type="number" value={f.alpha_min} onChange={e => setF({ ...f, alpha_min: +e.target.value })} /></div>
          <div><label>α max (°)</label><input type="number" value={f.alpha_max} onChange={e => setF({ ...f, alpha_max: +e.target.value })} /></div>
          <div><label>Pas (°)</label><input type="number" step="0.5" value={f.step} onChange={e => setF({ ...f, step: +e.target.value })} /></div>
          <div><label>Reynolds</label><input type="number" value={f.re} onChange={e => setF({ ...f, re: +e.target.value })} /></div>
          <div><label>Allongement (AR)</label><input placeholder="ex : 8" value={f.ar} onChange={e => setF({ ...f, ar: e.target.value })} /></div>
          <div><label>α analyse (°)</label><input type="number" value={f.alpha_deg} onChange={e => setF({ ...f, alpha_deg: +e.target.value })} /></div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="p" onClick={() => post('/api/cfd/airfoil/sweep', body).then(setSweep).catch(e => setMsg(e.message))}>
            Balayage CL/CD</button>
          <button onClick={() => post('/api/cfd/airfoil/solve', body).then(setSingle).catch(e => setMsg(e.message))}>
            Résoudre à α = {f.alpha_deg}°</button>
          <button onClick={async () => { try {
            const r = await post('/api/cfd/airfoil/field', { code: f.code, alpha_deg: f.alpha_deg })
            const url = `${location.origin}${r.url}?token=${localStorage.getItem('am_token')}`
            setGlance(`https://kitware.github.io/paraview-glance/?fileURL=${encodeURIComponent(url)}`)
          } catch (e) { setMsg(e.message) } }}>Champ de vitesse → ParaView Glance</button>
        </div>
        {msg && <p className="sm" style={{ color: 'var(--bad)' }}>{msg}</p>}
      </div>
      {sweep && <div className="grid">
        <div className="card"><h3>CL vs α</h3>
          <LineChart series={[{ label: 'CL (avec décrochage)', points: sweep.alpha.map((a, i) => [a, sweep.cl_eff[i]]), color: '#38bdf8' },
            { label: 'CL inviscide', points: sweep.alpha.map((a, i) => [a, sweep.cl[i]]), color: '#818cf8' }]}
            xLabel="α (°)" yLabel="CL" /></div>
        <div className="card"><h3>CD vs α</h3>
          <LineChart series={[{ label: 'CD estimé', points: sweep.alpha.map((a, i) => [a, sweep.cd[i]]), color: '#f59e0b' }]}
            xLabel="α (°)" yLabel="CD" /></div>
        <div className="card"><h3>Finesse CL/CD</h3>
          <LineChart series={[{ label: 'L/D', points: sweep.alpha.map((a, i) => [a, sweep.ldr[i]]), color: '#34d399' }]}
            xLabel="α (°)" yLabel="L/D" /></div>
      </div>}
      {single && <div className="card">
        <h3>NACA {single.code} — α = {single.alpha_deg}°, Re = {single.re.toExponential(0)}</h3>
        <div className="kv">
          <div><span className="mut sm">CL (panneaux)</span><b>{single.cl}</b></div>
          <div><span className="mut sm">CL (Γ, Kutta)</span><b>{single.cl_kutta_gamma}</b></div>
          <div><span className="mut sm">CL effectif</span><b>{single.cl_eff}</b></div>
          <div><span className="mut sm">CD estimé</span><b>{single.cd_est}</b></div>
        </div>
        <h3 style={{ marginTop: 10 }}>Distribution de Cp</h3>
        <LineChart series={[{ label: 'Cp', points: single.x_mid.map((x, i) => [x, single.cp[i]]), color: '#38bdf8' }]}
          xLabel="x/c" yLabel="Cp" />
      </div>}
      {glance && <div className="modal"><div style={{ height: '92vh', display: 'flex', flexDirection: 'column' }}>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h2>ParaView Glance — champ de vitesse & Cp</h2>
          <button onClick={() => setGlance(null)}>Fermer</button>
        </div>
        <iframe src={glance} style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, background: '#fff' }} />
      </div></div>}
    </>
  )
}