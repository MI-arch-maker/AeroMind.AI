import React, { useEffect, useState } from 'react'
import { get, post, getText } from '../api.js'

const STATUS = { draft: ['b-mut', 'Brouillon'], submitted: ['b-warn', 'Soumis'],
  pending_dual: ['b-warn', '2ᵉ approb. requise'], authorized: ['b-ok', 'AUTORISÉ'],
  rejected: ['b-bad', 'Rejeté'] }
const isAdmin = u => ['admin', 'super_admin'].includes(u.role)

export default function FlightOps({ user }) {
  const [reqs, setReqs] = useState([])
  const [sel, setSel] = useState(null)
  const [dossier, setDossier] = useState(null)
  const [msg, setMsg] = useState('')
  const refresh = () => get('/api/flightops/requests').then(setReqs)
  useEffect(() => { refresh() }, [])
  useEffect(() => { if (sel) get('/api/flightops/requests/' + sel).then(setSel).catch(() => {}) }, [sel?.id])
  return (
    <>
      <h1>Vols — autorisations internes & dossier DGAC/SORA</h1>
      <div className="grid">
        <ZoneChecker />
        <NewRequest onDone={r => { setMsg('Demande ' + r.id + ' créée' +
          (r.zone_check.ok ? ' — zone conforme ✓' : ' — ⚠ avertissements de zone')); refresh() }} />
      </div>
      {msg && <p className="sm mut">{msg}</p>}
      <div className="card">
        <h2>Demandes de vol</h2>
        <table>
          <thead><tr><th>ID</th><th>Aéronef</th><th>Opérateur</th><th>Statut</th><th>Autorisation</th></tr></thead>
          <tbody>
            {reqs.map(r => (
              <tr key={r.id} style={{ cursor: 'pointer', background: sel?.id === r.id ? '#16233c' : '' }}
                  onClick={() => setSel(r)}>
                <td>{r.id}</td><td>{r.uas_name}</td><td>{r.operator_name}</td>
                <td><span className={'badge ' + (STATUS[r.status] || ['b-mut', r.status])[0]}>
                  {(STATUS[r.status] || ['b-mut', r.status])[1]}</span></td>
                <td>{r.auth_serial || '—'}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      {sel && <Detail req={sel} user={user} onUpdate={r => { setSel(r); refresh() }}
        onDossier={setDossier} />}
      {dossier && <DossierModal d={dossier} onClose={() => setDossier(null)} />}
    </>
  )
}

function ZoneChecker() {
  const [f, setF] = useState({ lat: 43.6045, lon: 1.4442, alt_m: 100 })
  const [r, setR] = useState(null)
  return (
    <div className="card">
      <h2>Contrôle de zone</h2>
      <label>Latitude</label><input type="number" step="0.0001" value={f.lat} onChange={e => setF({ ...f, lat: +e.target.value })} />
      <label>Longitude</label><input type="number" step="0.0001" value={f.lon} onChange={e => setF({ ...f, lon: +e.target.value })} />
      <label>Altitude (m)</label><input type="number" value={f.alt_m} onChange={e => setF({ ...f, alt_m: +e.target.value })} />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="p" onClick={() => post('/api/flightops/zones/check', f).then(setR)}>Vérifier</button>
      </div>
      {r && <div className="sm" style={{ marginTop: 8 }}>
        {r.ok ? <span style={{ color: 'var(--ok)' }}>✓ Zone conforme (CTR échantillon + plafond 120 m)</span>
          : <ul style={{ color: 'var(--bad)', margin: '4px 0', paddingLeft: 18 }}>
              {r.violations.map((v, i) => <li key={i}>{v}</li>)}</ul>}
      </div>}
    </div>
  )
}

function NewRequest({ onDone }) {
  const [f, setF] = useState({ operator_name: 'MI-arch', operator_contact: 'ops@aeromind.local',
    uas_name: 'AM-Alpha 3500', uas_class: 'C2', mtom_g: 3500, op_category: 'A3',
    purpose: 'Essais de performance', center_lat: 43.6045, center_lon: 1.4442, radius_m: 500,
    alt_min_m: 0, alt_max_m: 100, start_utc: '2025-01-01T09:00', end_utc: '2025-01-01T11:00',
    population: 'sparse', airspace: 'a', mitigations: ['geo_awareness'] })
  const set = (k, v) => setF({ ...f, [k]: v })
  return (
    <div className="card">
      <h2>Nouvelle demande de vol</h2>
      <div className="grid">
        <div><label>Opérateur</label><input value={f.operator_name} onChange={e => set('operator_name', e.target.value)} /></div>
        <div><label>Contact</label><input value={f.operator_contact} onChange={e => set('operator_contact', e.target.value)} /></div>
        <div><label>Aéronef</label><input value={f.uas_name} onChange={e => set('uas_name', e.target.value)} /></div>
        <div><label>Classe UAS</label><select value={f.uas_class} onChange={e => set('uas_class', e.target.value)}>
          {['C0', 'C1', 'C2', 'C3', 'C4', 'non classé'].map(c => <option key={c}>{c}</option>)}</select></div>
        <div><label>MTOM (g)</label><input type="number" value={f.mtom_g} onChange={e => set('mtom_g', +e.target.value)} /></div>
        <div><label>Catégorie</label><select value={f.op_category} onChange={e => set('op_category', e.target.value)}>
          {['A1', 'A2', 'A3', 'Spécifique'].map(c => <option key={c}>{c}</option>)}</select></div>
        <div><label>Lat centre</label><input type="number" step="0.0001" value={f.center_lat} onChange={e => set('center_lat', +e.target.value)} /></div>
        <div><label>Lon centre</label><input type="number" step="0.0001" value={f.center_lon} onChange={e => set('center_lon', +e.target.value)} /></div>
        <div><label>Rayon (m)</label><input type="number" value={f.radius_m} onChange={e => set('radius_m', +e.target.value)} /></div>
        <div><label>Alt max (m)</label><input type="number" value={f.alt_max_m} onChange={e => set('alt_max_m', +e.target.value)} /></div>
        <div><label>Densité pop.</label><select value={f.population} onChange={e => set('population', e.target.value)}>
          <option value="sparse">dispersée</option><option value="moderate">moyenne</option><option value="dense">dense</option></select></div>
        <div><label>Espace aérien (ARC)</label><select value={f.airspace} onChange={e => set('airspace', e.target.value)}>
          {['a', 'b', 'c', 'd'].map(c => <option key={c}>{c}</option>)}</select></div>
      </div>
      <div className="row sm" style={{ margin: '8px 0' }}>
        {['parachute', 'geo_awareness'].map(m => (
          <label key={m} style={{ display: 'flex', gap: 6, alignItems: 'center', margin: 0 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={f.mitigations.includes(m)}
              onChange={e => set('mitigations', e.target.checked
                ? [...f.mitigations, m] : f.mitigations.filter(x => x !== m))} /> {m}</label>))}
      </div>
      <button className="p" onClick={() => post('/api/flightops/requests', f).then(onDone)}>Créer (brouillon)</button>
    </div>
  )
}

function Detail({ req, user, onUpdate, onDossier }) {
  const [comment, setComment] = useState('')
  const act = (path, body) => post(`/api/flightops/requests/${req.id}/${path}`, body || {})
    .then(onUpdate).catch(e => alert(e.message))
  return (
    <div className="card">
      <h2>{req.id} — {req.uas_name} <span className={'badge ' + (STATUS[req.status] || ['b-mut', ''])[0]}>
        {(STATUS[req.status] || ['b-mut', req.status])[1]}</span></h2>
      <div className="kv sm">
        <div><span className="mut">Zone</span><br />{req.center_lat?.toFixed(4)}, {req.center_lon?.toFixed(4)} ±{req.radius_m} m</div>
        <div><span className="mut">Altitudes</span><br />{req.alt_min_m}–{req.alt_max_m} m</div>
        <div><span className="mut">Créneau</span><br />{req.start_utc} → {req.end_utc}</div>
        <div><span className="mut">Autorisation</span><br />{req.auth_serial || '—'}</div>
        <div><span className="mut">Contrôle zone</span><br />
          {(req.zone_check || {}).ok ? '✓ conforme' : '⚠ ' + ((req.zone_check || {}).violations || []).join(' ; ')}</div>
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        {req.status === 'draft' && (isAdmin(user) || req.created_by === user.username) &&
          <button className="p" onClick={() => act('submit')}>Soumettre à revue</button>}
        {req.status === 'submitted' && isAdmin(user) && <>
          <input placeholder="commentaire" value={comment} onChange={e => setComment(e.target.value)} style={{ maxWidth: 240 }} />
          <button className="p" onClick={() => act('review', { decision: 'approve', comment })}>Approuver (1ʳᵉ)</button>
          <button onClick={() => act('review', { decision: 'reject', comment })}>Rejeter</button></>}
        {req.status === 'pending_dual' && isAdmin(user) &&
          <button className="p" onClick={() => act('confirm')}>Confirmer (2ᵉ approbateur ≠ 1ᵉʳ)</button>}
        <button onClick={() => post(`/api/flightops/requests/${req.id}/dossier`, {})
          .then(async r => onDossier({ ...r, md: await getText(`${r.url}?token=${localStorage.getItem('am_token')}`) }))
          .catch(e => alert(e.message))}>Générer le dossier DGAC/SORA</button>
      </div>
    </div>
  )
}

function DossierModal({ d, onClose }) {
  return (
    <div className="modal"><div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>Dossier de préparation — SAIL estimé : {d.sora.sail}</h2>
        <button onClick={onClose}>Fermer</button>
      </div>
      <p className="sm mut">GRC final {d.sora.final_grc} · ARC {d.sora.arc.toUpperCase()} — {d.sora.note}</p>
      <pre>{d.md}</pre>
    </div></div>
  )
}