import React, { useEffect, useRef, useState } from 'react'
import { get, post, del } from '../api.js'
import { DualBox } from '../ui.jsx'

export default function Bench() {
  const [sessions, setSessions] = useState([])
  const [sid, setSid] = useState(null)
  const [detail, setDetail] = useState(null)
  const [tel, setTel] = useState(null)
  const [kind, setKind] = useState('quad')
  const [fr, setFr] = useState('')
  const [mission, setMission] = useState('[{"x":40,"y":0,"z":10},{"x":40,"y":50,"z":15},{"x":-30,"y":40,"z":8}]')
  const [g, setG] = useState({ x: 0, y: 0, z: 10 })
  const refresh = () => get('/api/bench/sessions').then(setSessions)
  useEffect(() => { refresh() }, [])
  useEffect(() => {
    if (!sid) return
    setTel(null)
    get('/api/bench/sessions/' + sid).then(setDetail).catch(() => {})
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/bench/ws/${sid}?token=${localStorage.getItem('am_token')}`)
    ws.onmessage = e => setTel(JSON.parse(e.data))
    wsRef.current = ws
    return () => ws.close()
  }, [sid])
  const wsRef = useRef(null)
  const S = id => post(`/api/bench/sessions/${sid}/${id}`)
  return (
    <>
      <h1>Banc d'essai virtuel — temps réel</h1>
      <div className="card">
        <div className="row">
          <select value={kind} onChange={e => setKind(e.target.value)}>
            <option value="quad">Multirotor (6 DDL)</option>
            <option value="fw">Voilure fixe</option>
            <option value="external">SITL externe (MAVLink)</option>
          </select>
          <input placeholder="ID demande de vol (optionnel)" value={fr} onChange={e => setFr(e.target.value)} style={{ maxWidth: 240 }} />
          <button className="p" onClick={() => post('/api/bench/sessions',
            { kind, flight_request_id: fr || null, params: {} })
            .then(r => { refresh(); setSid(r.id) }).catch(e => alert(e.message))}>Créer une session</button>
        </div>
        <table style={{ marginTop: 10 }}>
          <thead><tr><th>ID</th><th>Type</th><th>Créée par</th><th>Vol lié</th><th></th></tr></thead>
          <tbody>{sessions.map(s => (
            <tr key={s.id} style={{ background: sid === s.id ? '#16233c' : '' }}>
              <td style={{ cursor: 'pointer' }} onClick={() => setSid(s.id)}>{s.id}</td>
              <td>{s.kind}</td><td>{s.created_by}</td><td>{s.flight_request_id || '—'}</td>
              <td><button className="danger" onClick={() => del('/api/bench/sessions/' + s.id).then(refresh)}>✕</button></td>
            </tr>))}</tbody>
        </table>
      </div>
      {sid && tel && <>
        <div className="grid">
          <div className="card">
            <h3>Attitude & énergie</h3>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <Attitude rpy={tel.rpy} />
              <div className="kv">
                <div><span className="mut sm">Mode</span><b>{tel.mode}</b></div>
                <div><span className="mut sm">Armé</span><b>{tel.armed ? 'OUI' : 'non'}</b></div>
                <div><span className="mut sm">t (s)</span><b>{tel.t}</b></div>
                <div><span className="mut sm">Batterie</span><b>{Math.round(tel.soc * 100)}%</b></div>
              </div>
            </div>
            <div className="bar" style={{ margin: '10px 0' }}>
              <i style={{ width: `${tel.soc * 100}%`, background: tel.soc > 0.2 ? 'var(--ok)' : 'var(--bad)' }} /></div>
            <div className="kv sm">
              <div><span className="mut">V bat</span><br />{tel.vbat} V</div>
              <div><span className="mut">WP</span><br />{tel.wp + 1}/{tel.n_wp || 0}</div>
              <div><span className="mut">Alt</span><br />{tel.pos[2]} m</div>
              <div><span className="mut">Vitesse</span><br />{Math.hypot(...tel.vel).toFixed(1)} m/s</div>
            </div>
            {tel.motors_rpm && <p className="sm mut">Moteurs : {tel.motors_rpm.join(' / ')} tr/min · poussée {tel.thrust_n} N</p>}
          </div>
          <div className="card">
            <h3>Carte locale (m)</h3>
            <MapView tel={tel} mission={(detail?.mission) || []} />
          </div>
        </div>
        <DualBox label="Armement moteur" action="bench_arm" target={sid}
          onReady={token => S('arm').then(() => post(`/api/bench/sessions/${sid}/arm`, { dual_token: token }))} />
        <div className="card">
          <h3>Contrôles</h3>
          <div className="row">
            <button onClick={() => S('disarm').catch(e => alert(e.message))}>Désarmer</button>
            {['HOLD', 'MISSION', 'LAND', 'RTL'].map(m =>
              <button key={m} onClick={() => post(`/api/bench/sessions/${sid}/mode`, { mode: m }).catch(e => alert(e.message))}>{m}</button>)}
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <div><label>x (m)</label><input type="number" style={{ width: 90 }} value={g.x} onChange={e => setG({ ...g, x: +e.target.value })} /></div>
            <div><label>y (m)</label><input type="number" style={{ width: 90 }} value={g.y} onChange={e => setG({ ...g, y: +e.target.value })} /></div>
            <div><label>z (m)</label><input type="number" style={{ width: 90 }} value={g.z} onChange={e => setG({ ...g, z: +e.target.value })} /></div>
            <button onClick={() => post(`/api/bench/sessions/${sid}/goto`, g).catch(e => alert(e.message))}>Aller à</button>
          </div>
          <label>Mission (JSON — {`{x,y,z}`} local ou {`{lat,lon,alt}`})</label>
          <textarea rows="3" value={mission} onChange={e => setMission(e.target.value)} />
          <div className="row" style={{ marginTop: 8 }}>
            <button className="p" onClick={() => post(`/api/bench/sessions/${sid}/mission`,
              { waypoints: JSON.parse(mission) })
              .then(r => alert(r.warnings.length ? '⚠ ' + r.warnings.join('\n') : 'Mission chargée'))
              .catch(e => alert('JSON invalide ou ' + e.message))}>Téléverser la mission</button>
          </div>
        </div>
        {tel.violations?.length > 0 && <div className="card">
          <h3 style={{ color: 'var(--bad)' }}>Violations</h3>
          <ul style={{ paddingLeft: 18 }}>{tel.violations.map((v, i) => <li key={i} className="sm">{v}</li>)}</ul>
        </div>}
      </>}
    </>
  )
}

function Attitude({ rpy }) {
  const [r, p, y] = rpy || [0, 0, 0]
  return (
    <svg viewBox="0 0 160 160" style={{ width: 150, background: '#0a101d', borderRadius: '50%', border: '1px solid var(--line)' }}>
      <clipPath id="c"><circle cx="80" cy="80" r="74" /></clipPath>
      <g clipPath="url(#c)"><g transform={`rotate(${-r} 80 80) translate(0 ${p * 2.2})`}>
        <rect x="-60" y="-160" width="280" height="240" fill="#132a3f" />
        <rect x="-60" y="80" width="280" height="240" fill="#4a3venue0" />
        <rect x="-60" y="80" width="280" height="240" fill="#4a3210" />
        <line x1="-60" y1="80" x2="220" y2="80" stroke="#e2e8f0" strokeWidth="2" />
      </g></g>
      <circle cx="80" cy="80" r="74" fill="none" stroke="var(--line)" />
      <line x1="60" y1="80" x2="74" y2="80" stroke="#f59e0b" strokeWidth="3" />
      <line x1="86" y1="80" x2="100" y2="80" stroke="#f59e0b" strokeWidth="3" />
      <circle cx="80" cy="80" r="2.5" fill="#f59e0b" />
      <text x="80" y="18" fill="#8ea0bf" fontSize="9" textAnchor="middle">{Math.round(((y || 0) + 360) % 360)}°</text>
    </svg>
  )
}

function MapView({ tel, mission }) {
  const trail = tel.trail || [], pos = tel.pos || [0, 0, 0], home = tel.home || [0, 0, 0]
  const pts = [...trail, pos, home, ...mission]
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]), pad = 15
  const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad
  const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad
  const W = 440, H = 330
  const sx = v => (v - x0) / (x1 - x0 || 1) * W
  const sy = v => H - (v - y0) / (y1 - y0 || 1) * H
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', background: '#0a101d', border: '1px solid var(--line)', borderRadius: 8 }}>
      {trail.length > 1 && <polyline fill="none" stroke="#38bdf8" strokeWidth="1.5" opacity="0.7"
        points={trail.map(p => `${sx(p[0])},${sy(p[1])}`).join(' ')} />}
      {mission.map((w, i) => <g key={i}>
        <circle cx={sx(w[0])} cy={sy(w[1])} r="5" fill="none" stroke="#34d399" />
        <text x={sx(w[0]) + 8} y={sy(w[1]) + 3} fill="#34d399" fontSize="10">{i + 1}</text></g>)}
      <g stroke="#f59e0b">
        <line x1={sx(home[0]) - 6} x2={sx(home[0]) + 6} y1={sy(home[1])} y2={sy(home[1])} />
        <line x1={sx(home[0])} x2={sx(home[0])} y1={sy(home[1]) - 6} y2={sy(home[1]) + 6} /></g>
      <g transform={`translate(${sx(pos[0])},${sy(pos[1])}) rotate(${90 - (tel.rpy?.[2] || 0)})`}>
        <polygon points="0,-8 5,7 -5,7" fill="#f87171" /></g>
    </svg>
  )
}