import { User, Session } from '../types'

// Resolve backend URL
export const API_BASE = (import.meta.env.VITE_BACKEND_URL as string) || 'http://localhost:8000'

export function getAccessToken(): string | null {
  return localStorage.getItem('omniagent_token')
}

export function setAccessToken(token: string): void {
  localStorage.setItem('omniagent_token', token)
}

export function clearAccessToken(): void {
  localStorage.removeItem('omniagent_token')
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAccessToken()
  return {
    'Authorization': `Bearer ${token || ''}`,
    'Content-Type': 'application/json'
  }
}

export async function loginWithGoogle(idToken: string): Promise<{ access_token: string; user: User }> {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: idToken })
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Google Authentication failed.')
  }
  const data = await res.json()
  setAccessToken(data.access_token)
  return data
}

export async function saveKeys(groqKey: string, tavilyKey: string): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/keys/save`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ groq_key: groqKey, tavily_key: tavilyKey })
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to save credentials.')
  }
  return res.json()
}

export async function getKeys(): Promise<{ groq_key_masked: string; tavily_key_masked: string }> {
  const res = await fetch(`${API_BASE}/keys/get`, {
    method: 'GET',
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to fetch credentials.')
  }
  return res.json()
}

export async function getHistory(limit: number = 20): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/history?limit=${limit}`, {
    method: 'GET',
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to load session history.')
  }
  return res.json()
}

export async function searchHistory(query: string): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/history/search?q=${encodeURIComponent(query)}`, {
    method: 'GET',
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to complete history search.')
  }
  return res.json()
}
