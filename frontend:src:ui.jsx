import React, { useState } from 'react'
import { post } from './api.js'

const COLORS = ['#38bdf8', '#34d399', '#f59e0b', '#818cf8', '#f87171']

export function LineChart({ series, xLabel = '', yLabel = '', height = 260 }) {
  const W = 620, H = height, L = 52, R = 14, T = 12, B = 34
  const pts = series.flatMap(s => s.points || [])
  if (!pts.length) return <div className="mut">Pas de données</div>
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1])
  const x0 = Math.min(...xs), x1 = Math.max(...xs)
  let y0 = Math.min(0, ...ys), y1 = Math.max(0, ...ys)
  if (y1 === y0) y1 = y0 + 1
  const sx = v => L + (v - x0) / (x1 - x0 || 1) * (W - L - R)
  const sy = v => H - B - (v - y0) / (y1 - y0) * (H - T - B)
  const ticks = (a, b, n = 5) => Array.from({ length: n }, (_, i) => a + (b - a) * i / (n - 1))
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', background: '#0a101d', border: '1px solid var(--line)', borderRadius: 8 }}>
        {ticks(y0, y1).map((t, i) => (
          <g key={i}><line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} stroke="#1f2b45" strokeDasharray="3 4" />
            <text x={L - 6} y={sy(t) + 4} fill="#8ea0bf" fontSize="10" textAnchor="end">{t.toFixed(Math.abs(y1 - y0) < 3 ? 2 : 0)}</text></g>))}
        {ticks(x0, x1).map((t, i) => (
          <g key={i}><line x1={sx(t)} x2={sx(t)} y1={T} y2={H - B} stroke="#1f2b45" strokeDasharray="3 4" />
            <text x={sx(t)} y={H - B + 14} fill="#8ea0bf" fontSize="10" textAnchor="middle">{t.toFixed(1)}</text></g>))}
        {series.map((s, i) => (
          <polyline key={i} fill="none" stroke={s.color || COLORS[i % 5]} strokeWidth="2"
            points={(s.points || []).map(p => `${sx(p[0])},${sy(p[1])}`).join(' ')} />))}
        <text x={(W + L) / 2} y={H - 4} fill="#8ea0bf" fontSize="10" textAnchor="middle">{xLabel}</text>
        <text x={12} y={H / 2} fill="#8ea0bf" fontSize="10" textAnchor="middle" transform={`rotate(-90 12 ${H / 2})`}>{yLabel}</text>
      </svg>
      <div className="row sm" style={{ marginTop: 4 }}>
        {series.map((s, i) => <span key={i} style={{ color: s.color || COLORS[i % 5] }}>■ {s.label || s.key}</span>)}
      </div>
    </div>
  )
}

export function DualBox({ label = 'Action sensible', action, target, onReady }) {
  const [token, setToken] = useState('')
  const [msg, setMsg] = useState('')
  return (
    <div className="card">
      <b>{label}</b> <span className="mut sm">— règle des deux personnes (2 approbateurs distincts, TTL 10 min)</span>
      <div className="row" style={{ marginTop: 8 }}>
        <button onClick={async () => { try {
          const r = await post('/api/auth/dual', { action, target })
          setToken(r.token); setMsg('Jeton créé — à faire confirmer par un 2ᵉ admin (autre onglet/compte).')
        } catch (e) { setMsg('⛔ ' + e.message) } }}>1. Demander (admin)</button>
        <input style={{ maxWidth: 250 }} placeholder="coller le jeton" value={token} onChange={e => setToken(e.target.value)} />
        <button onClick={async () => { try {
          const r = await post(`/api/auth/dual/${token}/confirm`); setMsg('✓ ' + r.status)
        } catch (e) { setMsg('⛔ ' + e.message) } }}>2. Confirmer (autre admin)</button>
        <button className="p" onClick={async () => { try { await onReady(token) } catch (e) { setMsg('⛔ ' + e.message) } }}>3. Exécuter</button>
      </div>
      {msg && <div className="sm mut" style={{ marginTop: 6 }}>{msg}</div>}
    </div>
  )
}