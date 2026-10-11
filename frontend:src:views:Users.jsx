import React, { useEffect, useState } from 'react'
import { get, post } from '../api.js'

export default function Users() {
  const [users, setUsers] = useState([])
  const [f, setF] = useState({ username: '', password: '', role: 'operator' })
  const refresh = () => get('/api/auth/users').then(setUsers)
  useEffect(() => { refresh() }, [])
  return (
    <>
      <h1>Utilisateurs (super-admin)</h1>
      <div className="card">
        <div className="row">
          <div><label>Identifiant</label><input value={f.username} onChange={e => setF({ ...f, username: e.target.value })} /></div>
          <div><label>Mot de passe</label><input type="password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} /></div>
          <div><label>Rôle</label><select value={f.role} onChange={e => setF({ ...f, role: e.target.value })}>
            {['viewer', 'operator', 'admin', 'super_admin'].map(r => <option key={r}>{r}</option>)}</select></div>
          <button className="p" onClick={() => post('/api/auth/users', f).then(refresh).catch(e => alert(e.message))}>Créer</button>
        </div>
      </div>
      <div className="card">
        <table><thead><tr><th>Identifiant</th><th>Rôle</th><th>Créé le</th></tr></thead>
          <tbody>{users.map(u => <tr key={u.username}><td>{u.username}</td><td>{u.role}</td><td className="sm">{u.created_at}</td></tr>))}</tbody>
        </table>
      </div>
    </>
  )
}