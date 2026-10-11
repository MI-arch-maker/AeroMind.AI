import React, { useEffect, useState } from 'react'
import { get } from '../api.js'

const Card = ({ title, ok, main, sub }) => (
  <div className="card">
    <h3>{title}</h3>
    <div style={{ fontSize: 20, fontWeight: 600,
      color: ok === null ? 'var(--tx)' : ok ? 'var(--ok)' : 'var(--warn)' }}>{main}</div>
    <div className="sm mut">{sub}</div>
  </div>
)

export default function Dashboard({ user }) {
  const [d, setD] = useState(null)
  useEffect(() => {
    const safe = p => get(p).catch(e => ({ __err: e.message }))
    Promise.all([safe('/api/health'), safe('/api/cfd/capabilities'), safe('/api/propulsion/sources'),
      safe('/api/flightops/requests'), safe('/api/cert'), safe('/api/bench/sessions'),
      safe('/api/audit/verify')])
      .then(([health, cfd, prop, flights, certs, bench, audit]) =>
        setD({ health, cfd, prop, flights, certs, bench, audit }))
  }, [])
  if (!d) return <p className="mut">Chargement…</p>
  const nAuth = (d.flights || []).filter(r => r.status === 'authorized').length
  return (
    <>
      <h1>Vue d'ensemble — centre opérationnel</h1>
      <div className="grid">
        <Card title="Service" ok={d.health?.status === 'ok'}
          main={d.health?.status === 'ok' ? 'EN LIGNE' : 'ERREUR'}
          sub={d.health ? `AeroMind.IA v${d.health.version} · connecté : ${user.username}` : 'inaccessible'} />
        <Card title="CFD" ok={d.cfd?.openfoam}
          main={d.cfd?.openfoam ? 'Panneaux + OpenFOAM' : 'Panneaux (Hess–Smith)'}
          sub={d.cfd?.openfoam ? 'simpleFoam RANS disponible' : 'RANS : activer Dockerfile.openfoam (§ doc)'} />
        <Card title="Propulsion" ok={null}
          main={`${Object.keys(d.prop || {}).length} sources`}
          sub={Object.values(d.prop || {}).map(s => s.label).join(' · ')} />
        <Card title="Vols" ok={null} main={`${(d.flights || []).length} demandes`}
          sub={`${nAuth} autorisées · contrôle de zone + SORA simplifiée`} />
        <Card title="Certifications" ok={null} main={`${(d.certs || []).length} émises`}
          sub="Ed25519 · double approbation · vérifiables publiquement" />
        <Card title="Banc d'essai" ok={null} main={`${(d.bench || []).length} sessions`}
          sub="multirotor 6 DDL · voilure fixe · télémétrie temps réel" />
        <Card title="Journal d'audit" ok={d.audit?.valid}
          main={d.audit?.valid ? 'CHAÎNE INTÈGRE' : 'vérification indisponible'}
          sub={d.audit?.valid ? `${d.audit.entries} entrées chaînées SHA-256`
            : (d.audit?.__err || 'connexion admin requise')} />
      </div>
      <div className="card">
        <h3>Procédure de test complète</h3>
        <ol className="sm" style={{ paddingLeft: 18, lineHeight: 1.8 }}>
          <li><b>Vols</b> : créer → soumettre → approuver (admin) → confirmer (2ᵉ admin) → n° d'autorisation + dossier DGAC/SORA</li>
          <li><b>CFD</b> : balayage CL/CD −6°→16° · champ de vitesse → ParaView Glance</li>
          <li><b>Banc</b> : lier la session au vol autorisé → <b>armement moteur (2 admins)</b> → téléverser la mission → RTL/géorepérage</li>
          <li><b>Charge utile</b> : armer le largage civil (2 admins + zone conforme) → exécuter l'actionneur</li>
          <li><b>Certification</b> : relier drone + run CFD + session banc → émettre (2 admins) → vérifier la signature</li>
          <li><b>Audit</b> : vérifier la chaîne de hachage — chaque action ci-dessus y est inscrite</li>
        </ol>
      </div>
    </>
  )
}