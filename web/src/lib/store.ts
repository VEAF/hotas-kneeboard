// Application state: what the server read, what the user chose, and the pages built from both.

import { computed, reactive, ref, shallowRef } from 'vue'
import { api } from './api'
import type { BindingsResponse, DcsState, Device, Profile, Settings, Template, TemplateSummary } from './types'
import { canvasMeasurer, type Measurer } from '../render/text'
import { devicePages, type Page } from '../render/page'
import { FONT_CSS } from '../render/export'

export interface LoadedTemplate {
  data: Template
  image: string
}

const state = reactive({
  version: '',
  dcs: null as DcsState | null,
  settings: null as Settings | null,
  bindings: null as BindingsResponse | null,
  templates: [] as TemplateSummary[],
  loading: false,
  error: '' as string,
  profileName: '' as string,
  deviceKey: '' as string, // full name, with GUID: two devices may share a name
  filter: '',
  view: 'pages' as 'pages' | 'editor',
})

const templateCache = new Map<string, Promise<LoadedTemplate>>()
const measurer = shallowRef<Measurer | null>(null)

async function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}

export function loadTemplate(id: string): Promise<LoadedTemplate> {
  let pending = templateCache.get(id)
  if (!pending) {
    pending = (async () => {
      const [data, image] = await Promise.all([
        api.template(id),
        fetch(api.templateImageUrl(id)).then((r) => {
          if (!r.ok) throw new Error(`image du gabarit ${id} introuvable`)
          return r.blob()
        }),
      ])
      return { data, image: await blobToDataUrl(image) }
    })()
    pending.catch(() => templateCache.delete(id))
    templateCache.set(id, pending)
  }
  return pending
}

async function getMeasurer(): Promise<Measurer> {
  if (!measurer.value) {
    await Promise.all([
      document.fonts.load('600 12px "Barlow Condensed"'),
      document.fonts.load('700 12px "Barlow Condensed"'),
    ])
    measurer.value = canvasMeasurer()
  }
  return measurer.value
}

// --- reading -------------------------------------------------------------------------------

async function load(refresh = false): Promise<void> {
  state.loading = true
  state.error = ''
  try {
    const current = await api.state()
    state.version = current.version
    state.dcs = current.dcs
    state.settings = current.settings
    const [bindings, templates] = await Promise.all([api.bindings(refresh), api.templates()])
    state.bindings = bindings
    state.templates = templates
    if (refresh) templateCache.clear()
    const profiles = bindings.profiles
    if (!profiles.some((p) => p.name === state.profileName)) state.profileName = profiles[0]?.name ?? ''
    const devices = orderedDevices(profile.value)
    if (!devices.some((d) => d.full_name === state.deviceKey)) state.deviceKey = devices[0]?.full_name ?? ''
  } catch (error) {
    state.error = (error as Error).message
  } finally {
    state.loading = false
  }
}

// --- settings ------------------------------------------------------------------------------

let pendingChanges: Partial<Settings> = {}
let saveTimer: ReturnType<typeof setTimeout> | undefined

/** Applies at once, saves shortly after (several quick changes, one request) */
function changeSettings(changes: Partial<Settings>): void {
  if (!state.settings) return
  Object.assign(state.settings, changes)
  pendingChanges = { ...pendingChanges, ...changes }
  clearTimeout(saveTimer)
  saveTimer = setTimeout(flushSettings, 300)
}

async function flushSettings(): Promise<void> {
  const changes = pendingChanges
  pendingChanges = {}
  if (!Object.keys(changes).length) return
  try {
    const saved = await api.saveSettings(changes)
    state.dcs = saved.dcs
  } catch (error) {
    state.error = `Réglages non enregistrés : ${(error as Error).message}`
  }
}

/** Settings that change what is read from DCS: saved at once, then everything is read again */
async function saveReading(changes: Pick<Settings, 'dcs_install_dir' | 'saved_games_dir' | 'language'>): Promise<void> {
  if (!state.settings) return
  clearTimeout(saveTimer)
  await flushSettings()
  const saved = await api.saveSettings(changes)
  state.dcs = saved.dcs
  state.settings = saved.settings
  await load(true)
}

// --- derived -------------------------------------------------------------------------------

const profiles = computed<Profile[]>(() => state.bindings?.profiles ?? [])
const profile = computed<Profile | null>(() => profiles.value.find((p) => p.name === state.profileName) ?? null)

/** Devices in the user's order (drag and drop), the others after, by name */
function orderedDevices(p: Profile | null): Device[] {
  if (!p) return []
  const order = state.settings?.device_order[p.name] ?? []
  const rank = (d: Device) => {
    const i = order.indexOf(d.full_name)
    return i === -1 ? order.length : i
  }
  return [...p.devices].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name))
}

const devices = computed(() => orderedDevices(profile.value))
const device = computed<Device | null>(() => devices.value.find((d) => d.full_name === state.deviceKey) ?? null)

function isExported(profileName: string, d: Device): boolean {
  return state.settings?.exported[profileName]?.[d.full_name] ?? true
}

function templateIdFor(d: Device): string | null {
  const chosen = state.settings?.device_templates[d.name]
  // a choice of a template deleted since falls back to the automatic match
  if (chosen === '') return null
  if (chosen !== undefined && state.templates.some((t) => t.id === chosen)) return chosen
  return d.auto_template_id
}

// --- actions -------------------------------------------------------------------------------

function toggleExported(profileName: string, d: Device): void {
  if (!state.settings) return
  const exported = { ...state.settings.exported }
  exported[profileName] = { ...(exported[profileName] ?? {}), [d.full_name]: !isExported(profileName, d) }
  changeSettings({ exported })
}

function setTemplate(d: Device, templateId: string | null): void {
  if (!state.settings) return
  const device_templates = { ...state.settings.device_templates }
  if (templateId === d.auto_template_id) delete device_templates[d.name]
  else device_templates[d.name] = templateId ?? ''
  changeSettings({ device_templates })
}

function moveDevice(profileName: string, from: number, to: number): void {
  const p = profiles.value.find((x) => x.name === profileName)
  if (!p || !state.settings || from === to) return
  const names = orderedDevices(p).map((d) => d.full_name)
  if (to < 0 || to >= names.length) return
  const [moved] = names.splice(from, 1)
  names.splice(to, 0, moved)
  changeSettings({ device_order: { ...state.settings.device_order, [profileName]: names } })
}

async function pagesOf(profileName: string, d: Device): Promise<Page[]> {
  const id = templateIdFor(d)
  const [m, template] = await Promise.all([getMeasurer(), id ? loadTemplate(id) : Promise.resolve(null)])
  return devicePages(
    { profile: profileName, device: d, template, measurer: m, fontCss: FONT_CSS },
    state.settings?.layer_mode ?? 'merge',
  )
}

/** Every page of a module, in kneeboard order: exported devices only */
async function modulePages(p: Profile): Promise<Page[]> {
  const pages: Page[] = []
  for (const d of orderedDevices(p)) {
    if (isExported(p.name, d)) pages.push(...(await pagesOf(p.name, d)))
  }
  return pages
}

const busy = ref('')

export function useStore() {
  return {
    state,
    busy,
    profiles,
    profile,
    devices,
    device,
    load,
    changeSettings,
    saveReading,
    orderedDevices,
    isExported,
    templateIdFor,
    toggleExported,
    setTemplate,
    moveDevice,
    pagesOf,
    modulePages,
  }
}
