/**
 * Central API client
 * - Local dev: /api proxied to localhost:3001 via vite
 * - Production: uses VITE_API_URL env var (your Vercel backend URL)
 */

const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

function getToken() {
  return localStorage.getItem('cc_token')
}

function setToken(t) {
  if (t) localStorage.setItem('cc_token', t)
  else localStorage.removeItem('cc_token')
}

async function request(method, path, body) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (networkErr) {
    throw new Error('Cannot reach server. Make sure the backend is running.')
  }

  let data
  try {
    data = await res.json()
  } catch {
    throw new Error(`Server returned invalid response (${res.status})`)
  }

  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`)
    err.status = res.status
    err.code   = data.code
    throw err
  }

  if (data.token) setToken(data.token)
  return data
}

export const api = {
  get:    (path)        => request('GET',    path),
  post:   (path, body)  => request('POST',   path, body),
  delete: (path)        => request('DELETE', path),

  register: (name, email, password) =>
    request('POST', '/auth/register', { name, email, password }),
  login: (email, password) =>
    request('POST', '/auth/login', { email, password }),
  logout: () => { setToken(null); return request('POST', '/auth/logout') },
  me: () => request('GET', '/auth/me'),

  saveEntry:   (entry)        => request('POST',   '/entries', entry),
  getEntries:  (params = {})  => {
    const qs = new URLSearchParams(params).toString()
    return request('GET', `/entries${qs ? '?' + qs : ''}`)
  },
  getSummary:  ()             => request('GET', '/entries/summary'),
  deleteEntry: (date)         => request('DELETE', `/entries/${date}`),

  chat: (messages, summary)   => request('POST', '/chat', { messages, summary }),

  getToken,
  setToken,
  isLoggedIn: () => !!getToken(),
}
