import React, { useEffect, useState } from 'react'
import { get, post } from '../api.js'
import { DualBox } from '../ui.jsx'

export default function Payload({ user }) {
  const [cats, setCats] = useState([])
  const [releases, setReleases] = useState([])
  const [f, setF] = useState({ category: 'medical_drop', lat: 43.6045, lon: 1.4442, alt_m: 50 })
  const [msg, setMsg] = useState('')
  const isAdmin = ['admin', 'super_admin'].includes(user.role)
  const refresh = () => {
    get('/api/payload/categories').then(setCats).catch(() => {})
    get('/api/payload').then(setReleases).catch(e => setMsg(e.message))
  }
  useEffect(() => { refresh() }, [])
  const set = (k, v) => setF({ ...f, [k]: v })
  return (
    <>
      <h1>Charge utile — actionneur de largage civil</h1>
      <p className="sm mut">Catégories autorisées uniquement (largage humanitaire/medevac, balise,
        capteur, éclairage). Armement soumis à : catégorie valide + zone conforme (CTR/120 m) +
        <b> double approbation humaine</b>. Aucune fonction d'arme — voir note en bas d'écran.</p>
      {isAdmin && <div className="card">
        <h2>Armer un largage</h2>
        <div className="grid">
          <div><label>Catégorie</label>
            <select value={f.category} onChange={e => set('category', e.target.value)}>
              {cats.map(c => <option key={c} value={c}>{c}</option>)}</select></div>
          <div><label>Latitude</label><input type="number" step="0.0001" value={f.lat} onChange={e => set('lat', +e.target.value)} /></div>
          <div><label>Longitude</label><input type="number" step="0.0001" value={f.lon} onChange={e => set('lon', +e.target.value)} /></div>
          <div><label>Altitude (m)</label><input type="number" value={f.alt_m} onChange={e => set('alt_m', +e.target.value)} /></div>
        </div>
        <DualBox label={`Armement actionneur — ${f.category}`} action="payload_arm" target={f.category}
          onReady={token => post('/api/payload/arm', { ...f, dual_token: token })
            .then(r => { setMsg(`✓ Largage ${r.release_id} armé`); refresh() })} />
      </div>}
      {msg && <p className="sm mut">{msg}</p>}
      <div className="card">
        <h2>Largages</h2>
        <table>
          <thead><tr><th>ID</th><th>Catégorie</th><th>Position</th><th>Statut</th><th>Par</th><th></th></tr></thead>
          <tbody>{releases.map(r => (
            <tr key={r.id}><td>{r.id}</td><td>{r.category}</td>
              <td className="sm">{r.lat?.toFixed(4)}, {r.lon?.toFixed(4)} @ {r.alt_m} m</td>
              <td><span className={'badge ' + (r.status === 'executed' ? 'b-mut' : 'b-warn')}>{r.status}</span></td>
              <td className="sm">{r.created_by}</td>
              <td>{isAdmin && r.status === 'armed' &&
                <button className="p" onClick={() => post(`/api/payload/execute/${r.id}`)
                  .then(() => { setMsg('✓ Actionneur exécuté (simulé) — tracé dans l\'audit'); refresh() })
                  .catch(e => setMsg('⛔ ' + e.message))}>Exécuter</button>}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="sm mut">⚠ AeroMind.IA n'implémente aucune fonction d'armement d'arme ni de
        contre-mesure : interdit pour un opérateur privé (art. L6131-1 du code des transports).
        L'« armement » désigne ici l'armement moteur et l'activation d'actionneurs civils.</p>
    </>
  )
}