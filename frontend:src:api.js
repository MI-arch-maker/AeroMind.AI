const T = () => localStorage.getItem('am_token')
export async function api(path, opts = {}) {
  const r = await fetch(path, {
    ...opts,
    headers: { 'Content-Type': 'application/json',
      ...(T() ? { Authorization: 'Bearer ' + T() } : {}), ...(opts.headers || {}) }
  })
  if (r.status === 401) { localStorage.removeItem('am_token'); location.reload() }
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail || d))
  return d
}
export const post = (p, body) => api(p, { method: 'POST', body: JSON.stringify(body) })
export const get = p => api(p)
export const del = p => api(p, { method: 'DELETE' })
export async function getText(p) {
  const r = await fetch(p, { headers: { Authorization: 'Bearer ' + (T() || '') } })
  if (!r.ok) throw new Error('échec ' + r.status)
  return r.text()
}