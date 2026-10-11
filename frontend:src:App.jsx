import React, { useEffect, useState } from 'react'
import { get, post } from './api.js'
import Dashboard from './views/Dashboard.jsx'
import FlightOps from './views/FlightOps.jsx'
import Cfd from './views/Cfd.jsx'
import Bench from './views/Bench.jsx'
import Propulsion from './views/Propulsion.jsx'
import Certification from './views/Certification.jsx'
import Payload from './views/Payload.jsx'
import Audit from './views/Audit.jsx'
import Users from './views/Users.jsx'

const TABS = [['home', '🏠 Vue d\'ensemble'], ['flights', '✈ Vols & DGAC'], ['cfd', '🌀 CFD'],
  ['bench', '🛠 Banc d\'essai'], ['prop', '⚡ Propulsion'], ['cert', '📜 Certification'],
  ['payload', '📦 Charge utile'], ['audit', '🧾 Audit'], ['users', '👤 Utilisateurs']]

export default function App() {
  const [user, setUser] = useState(null)
  const [tab, setTab] = useState('home')
  useEffect(() => {
    const t = localStorage.getItem('am_token')
    if (t) get('/api/auth/me').then(setUser).catch(() => localStorage.removeItem('am_token'))
  }, [])
  if (!user) return <Login onLogin={setUser} />
  return (
    <>
      <nav>
        <b style={{ marginRight: 10 }}>AeroMind.IA</b>
        {TABS.filter(([k]) => k !== 'users' || user.role === 'super_admin').map(([k, l]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>))}
        <span style={{ marginLeft: 'auto' }} className="sm mut">{user.username} · {user.role}</span>
        <button onClick={() => { localStorage.removeItem('am_token'); location.reload() }}>Déconnexion</button>
      </nav>
      <main>
        {tab === 'home' && <Dashboard user={user} />}
        {tab === 'flights' && <FlightOps user={user} />}
        {tab === 'cfd' && <Cfd />}
        {tab === 'bench' && <Bench />}
        {tab === 'prop' && <Propulsion />}
        {tab === 'cert' && <Certification user={user} />}
        {tab === 'payload' && <Payload user={user} />}
        {tab === 'audit' && <Audit />}
        {tab === 'users' && <Users />}
      </main>
    </>
  )
}

function Login({ onLogin }) {
  const [f, setF] = useState({ username: '', password: '' })
  const [err, setErr] = useState('')
  return (
    <div className="modal"><div style={{ maxWidth: 400 }}>
      <h1>AeroMind.IA</h1>
      <p className="mut sm">Centre opérationnel — autorisations de vol internes, CFD, banc d'essai
        virtuel, propulsion, certification signée, audit chaîné.</p>
      <label>Identifiant</label>
      <input value={f.username} onChange={e => setF({ ...f, username: e.target.value })} />
      <label>Mot de passe</label>
      <input type="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
      <div className="row" style={{ marginTop: 12 }}>
        <button className="p" onClick={async () => {
          try { const r = await post('/api/auth/login', f)
            localStorage.setItem('am_token', r.token); onLogin(r) }
          catch (e) { setErr(e.message) } }}>Connexion</button>
      </div>
      {err && <p className="sm" style={{ color: 'var(--bad)' }}>{err}</p>}
      <p className="sm mut">admin@aeromind.local (super) · admin2@aeromind.local (admin) ·
        operator@aeromind.local (opérateur)</p>
    </div></div>
  )
}