import React, { useEffect, useState } from 'react'
import { get } from '../api.js'

export default function Audit() {
  const [rows, setRows] = useState([])
  const [v, setV] = useState(null)
  useEffect(() => { get('/api/audit?limit=300').then(setRows) }, [])
  return (
    <>
      <h1>Journal d'audit — chaînage SHA-256
        <button style={{ marginLeft: 12 }} onClick={() => get('/api/audit/verify').then(setV)}>Vérifier la chaîne</button></h1>
      {v && <p className={'badge ' + (v.valid ? 'b-ok' : 'b-bad')}>
        {v.valid ? `✓ Chaîne intègre (${v.entries} entrées)` : `⛔ Chaîne rompue à l'entrée #${v.first_broken_id}`}</p>}
      <div className="card">
        <table>
          <thead><tr><th>#</th><th>Horodatage</th><th>Acteur</th><th>Action</th><th>Cible</th><th>Empreinte</th></tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.id}><td>{r.id}</td><td className="sm">{r.ts}</td><td>{r.actor}</td>
              <td>{r.action}</td><td className="sm">{r.target}</td>
              <td className="sm mut">{r.entry_hash.slice(0, 16)}…</td></tr>))}</tbody>
        </table>
      </div>
    </>
  )
}