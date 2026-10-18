import type {
  BindingsResponse,
  DcsState,
  KneeboardResult,
  Settings,
  StateResponse,
  Template,
  TemplateSummary,
} from './types'

export class ApiError extends Error {}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch {
    throw new ApiError("Le serveur ne répond pas : l'application est-elle toujours lancée ?")
  }
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // not JSON: keep the status text
    }
    throw new ApiError(detail)
  }
  return response.json() as Promise<T>
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  state: () => request<StateResponse>('/api/state'),
  saveSettings: (changes: Partial<Settings>) =>
    request<{ dcs: DcsState; settings: Settings }>('/api/settings', json('PUT', changes)),
  bindings: (refresh = false) => request<BindingsResponse>(`/api/bindings${refresh ? '?refresh=true' : ''}`),
  templates: () => request<TemplateSummary[]>('/api/templates'),
  template: (id: string) => request<Template>(`/api/templates/${encodeURIComponent(id)}`),
  templateImageUrl: (id: string) => `/api/templates/${encodeURIComponent(id)}/image`,
  writeKneeboard: (unitType: string, pages: { title: string; png: string }[]) =>
    request<KneeboardResult>('/api/kneeboard', json('POST', { unit_type: unitType, pages })),
}
