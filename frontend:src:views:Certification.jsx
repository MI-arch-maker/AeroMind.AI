import React, { useEffect, useState } from 'react'
import { get, post } from '../api.js'
import { DualBox } from '../ui.jsx'

export default function Certification({ user }) {
  const [certs, setCerts] = useState([])
  const [f, setF] = useState({ drone_id: 'AM-Alpha-3500-001', cfd_run_id: '',
    bench_session_id: '', flight_request_id: '', notes: 'Essais CFD + banc conformes' })
  const [serial, setSerial] = useState('')
  const [v, setV] = useState(null)
  const [msg, setMsg] = useState('')
  const isAdmin = ['admin', 'super_admin'].includes(user.role)
  const refresh = () => get('/api/cert').then(setCerts).catch(e => setMsg(e.message))
  useEffect(() => { refresh() }, [])
  const set = (k, val) => setF({ ...f, [k]: val })
  return (
    <>
      <h1>Certification AeroMind.IA</h1>
      <p className="sm mut">Certificat INTERNE de performance signé Ed25519 : preuve d'intégrité et de
        traçabilité (référence les runs CFD, sessions de banc, vols autorisés). Sans valeur
        réglementaire DGAC/EASA. Émission sous double contrôle humain.</p>
      {isAdmin && <div className="card">
        <h2>Émettre un certificat</h2>
        <div className="grid">
          <div><label>Drone (ID)</label><input value={f.drone_id} onChange={e => set('drone_id', e.target.value)} /></div>
          <div><label>Référence run CFD</label><input placeholder="id cfd_runs" value={f.cfd_run_id} onChange={e => set('cfd_run_id', e.target.value)} /></div>
          <div><label>Session de banc</label><input placeholder="id session" value={f.bench_session_id} onChange={e => set('bench_session_id', e.target.value)} /></div>
          <div><label>Demande de vol liée</label><input placeholder="id flight_request" value={f.flight_request_id} onChange={e => set('flight_request_id', e.target.value)} /></div>
        </div>
        <label>Notes</label>
        <textarea rows="2" value={f.notes} onChange={e => set('notes', e.target.value)} />
        <DualBox label="Émission du certificat" action="cert_issue" target={f.drone_id}
          onReady={token => post('/api/cert/issue', { ...f, dual_token: token })
            .then(c => { setMsg(`✓ Certificat ${c.serial} émis`); refresh() })} />
      </div>}
      {msg && <p className="sm mut">{msg}</p>}
      <div className="card">
        <h2>Vérifier un certificat</h2>
        <div className="row">
          <input placeholder="numéro de série (ex : CERT-XXXX)" value={serial}
            onChange={e => setSerial(e.target.value)} style={{ maxWidth: 280 }} />
          <button className="p" onClick={() => get(`/api/cert/verify/${serial}`)
            .then(setV).catch(e => setV({ error: e.message }))}>Vérifier la signature</button>
        </div>
        {v && <div className="sm" style={{ marginTop: 8 }}>
          {v.error ? <span style={{ color: 'var(--bad)' }}>⛔ {v.error}</span> : <>
            <span className={'badge ' + (v.valid ? 'b-ok' : 'b-bad')}>
              {v.valid ? '✓ VALIDE (hash + signature Ed25519)' : '⛔ INVALIDE'}</span>
            <pre>{JSON.stringify(v.payload, null, 2)}</pre></>}
        </div>}
      </div>
      <div className="card">
        <h2>Certificats émis ({certs.length})</h2>
        <table>
          <thead><tr><th>N° série</th><th>Drone</th><th>Émis le</th><th>Émetteur</th><th>Approbateurs</th></tr></thead>
          <tbody>{certs.map(c => (
            <tr key={c.serial} style={{ cursor: 'pointer' }} onClick={() => setSerial(c.serial)}>
              <td>{c.serial}</td><td>{c.payload?.drone_id}</td>
              <td className="sm">{c.payload?.issued_at}</td><td>{c.payload?.issuer}</td>
              <td className="sm">{(c.payload?.approvers || []).join(' + ')}</td>
            </tr>))}</tbody>
        </table>
      </div>
    </>
  )
}