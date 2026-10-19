import type {
  BindingsResponse,
  DcsState,
  KneeboardResult,
  ProgramsResponse,
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
  programs: () => request<ProgramsResponse>('/api/programs'),
  templates: () => request<TemplateSummary[]>('/api/templates'),
  template: (id: string) => request<Template>(`/api/templates/${encodeURIComponent(id)}`),
  templateImageUrl: (id: string) => `/api/templates/${encodeURIComponent(id)}/image`,
  saveTemplate: (body: { template: Omit<Template, 'id' | 'image' | 'user'>; image_name: string; image: string; id: string | null }) =>
    request<TemplateSummary>('/api/templates', json('POST', body)),
  importTemplate: (file: string) => request<TemplateSummary>('/api/templates/import', json('POST', { file })),
  deleteTemplate: (id: string) => request<{ deleted: string }>(`/api/templates/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  templateFileUrl: (id: string) => `/api/templates/${encodeURIComponent(id)}/file`,
  writeKneeboard: (unitType: string, profile: string, pages: { title: string; png: string }[]) =>
    request<KneeboardResult>('/api/kneeboard', json('POST', { unit_type: unitType, profile, pages })),
}
