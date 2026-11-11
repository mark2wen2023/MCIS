import type { Role } from './types'

export const CASE_ID = 'CASE-2026-DEMO-LILY-MARY'
const BASE = '/api/v1'

let role: Role = (localStorage.getItem('mcis.role') as Role) || 'Investigator'
let operator = localStorage.getItem('mcis.operator') || '调查员 A'
const listeners = new Set<() => void>()

export function getRole(): Role { return role }
export function getOperator(): string { return operator }
export function setIdentity(r: Role, op?: string) {
  role = r
  if (op) operator = op
  localStorage.setItem('mcis.role', role)
  localStorage.setItem('mcis.operator', operator)
  listeners.forEach((f) => f())
}
export function onIdentityChange(f: () => void): () => void {
  listeners.add(f)
  return () => listeners.delete(f)
}

export class ApiError extends Error {
  status: number
  code: string
  detail: unknown
  constructor(status: number, code: string, message: string, detail: unknown) {
    super(message)
    this.status = status
    this.code = code
    this.detail = detail
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {
    'X-MCIS-Role': role,
    'X-MCIS-Operator': encodeURIComponent(operator),
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    throw new ApiError(res.status, data?.code ?? 'HTTP_' + res.status, data?.message ?? res.statusText, data?.detail)
  }
  return data as T
}

export const api = {
  get: <T,>(p: string) => request<T>('GET', p),
  post: <T,>(p: string, b: unknown = {}) => request<T>('POST', p, b),
  patch: <T,>(p: string, b: unknown) => request<T>('PATCH', p, b),
  put: <T,>(p: string, b: unknown) => request<T>('PUT', p, b),
}

export const casePath = (p: string) => `/cases/${CASE_ID}${p}`
