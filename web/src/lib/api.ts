import type {
  BindingRef,
  BindingsRemoved,
  BindingsResponse,
  DeviceBindingsResponse,
  GenericButtonsPreview,
  DcsBackup,
  DcsBackupsResponse,
  DcsDevicesResponse,
  HatViewsPreview,
  ModifiersFixed,
  ModifiersResponse,
  HatViewsResult,
  DcsState,
  KneeboardResult,
  ProgramsResponse,
  Settings,
  StateResponse,
  Template,
  TemplateSummary,
} from './types'
import { lang, t } from './i18n'

export class ApiError extends Error {}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    // the server answers in the interface's language
    response = await fetch(url, { ...init, headers: { 'Accept-Language': lang.value, ...init?.headers } })
  } catch {
    throw new ApiError(t('api.no_server'))
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
  /** the actions in `pages`, the language of the pages they are drawn on (the problems in the interface's) */
  programs: (pages: string) => request<ProgramsResponse>(`/api/programs?pages=${encodeURIComponent(pages)}`),
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
  dcsDevices: () => request<DcsDevicesResponse>('/api/dcs-config/devices'),
  setDeviceDisabled: (device: string, disabled: boolean) =>
    request<{ backup: DcsBackup }>('/api/dcs-config/devices/disabled', json('PUT', { device, disabled })),
  forgetDevice: (device: string) =>
    request<{ profiles: string[]; backup: DcsBackup }>('/api/dcs-config/devices/forget', json('POST', { device })),
  hatViews: (allModules: boolean) =>
    request<HatViewsPreview>(`/api/dcs-config/hat-views?all_modules=${allModules}`),
  removeHatViews: (devices: string[], everyDevice: boolean, allModules: boolean) =>
    request<HatViewsResult>(
      '/api/dcs-config/hat-views',
      json('POST', { devices, every_device: everyDevice, all_modules: allModules }),
    ),
  genericButtons: (allModules: boolean) =>
    request<GenericButtonsPreview>(`/api/dcs-config/generic-buttons?all_modules=${allModules}`),
  removeGenericButtons: (allModules: boolean) =>
    request<HatViewsResult>('/api/dcs-config/generic-buttons', json('POST', { all_modules: allModules })),
  modifiers: () => request<ModifiersResponse>('/api/dcs-config/modifiers'),
  fixModifiers: () => request<ModifiersFixed>('/api/dcs-config/modifiers/fix', { method: 'POST' }),
  restoreModifiers: (profile: string, backup: string) =>
    request<ModifiersFixed>('/api/dcs-config/modifiers/restore', json('POST', { profile, backup })),
  deviceBindings: (profile: string, device: string) =>
    request<DeviceBindingsResponse>(
      `/api/dcs-config/bindings?profile=${encodeURIComponent(profile)}&device=${encodeURIComponent(device)}`,
    ),
  removeBindings: (profile: string, device: string, bindings: BindingRef[]) =>
    request<BindingsRemoved>('/api/dcs-config/bindings/remove', json('POST', { profile, device, bindings })),
  dcsBackups: () => request<DcsBackupsResponse>('/api/dcs-config/backups'),
  createDcsBackup: () => request<DcsBackup>('/api/dcs-config/backups', { method: 'POST' }),
  restoreDcsBackup: (id: string) =>
    request<{ restored: string; backup_before: DcsBackup }>(`/api/dcs-config/backups/${encodeURIComponent(id)}/restore`, { method: 'POST' }),
}
