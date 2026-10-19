// Application state: what the server read, what the user chose, and the pages built from both.

import { computed, reactive, ref, shallowRef } from 'vue'
import { api } from './api'
import type {
  BindingsResponse,
  DcsState,
  Device,
  ManualProgramBinding,
  ProgramBinding,
  ProgramsResponse,
  Profile,
  Settings,
  Template,
  TemplateSummary,
} from './types'
import { canvasMeasurer, type Measurer } from '../render/text'
import { devicePages, type Page } from '../render/page'
import { FONT_CSS } from '../render/export'
import { marksFor, programStyles, SRS } from '../render/programs'
import { pageLanguage, setLanguage, t } from './i18n'

export interface LoadedTemplate {
  data: Template
  image: string
}

const state = reactive({
  version: '',
  dcs: null as DcsState | null,
  settings: null as Settings | null,
  bindings: null as BindingsResponse | null,
  /** buttons other programs use, as read from SRS and VectorXR */
  programs: null as ProgramsResponse | null,
  templates: [] as TemplateSummary[],
  loading: false,
  error: '' as string,
  profileName: '' as string,
  deviceKey: '' as string, // full name, with GUID: two devices may share a name
  filter: '',
  view: 'pages' as 'pages' | 'editor',
  /** list the hidden devices too (greyed), to show them again */
  showHidden: false,
  settingsFile: '',
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

/** Tooltip of a device whose layers use modifiers DCS drops (their device was renamed) */
export function inactiveHint(modifiers: string[]): string {
  return t('store.inactive_modifier', { names: modifiers.join(', ') })
}

export function loadTemplate(id: string): Promise<LoadedTemplate> {
  let pending = templateCache.get(id)
  if (!pending) {
    pending = (async () => {
      const [data, image] = await Promise.all([
        api.template(id),
        fetch(api.templateImageUrl(id)).then((r) => {
          if (!r.ok) throw new Error(t('store.template_image_missing', { id }))
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
    state.settingsFile = current.settings_file
    state.dcs = current.dcs
    state.settings = current.settings
    setLanguage(current.settings.ui_language)
    const [bindings, templates, programs] = await Promise.all([
      api.bindings(refresh),
      api.templates(),
      api.programs(pageLanguage(current.dcs.language)),
    ])
    state.bindings = bindings
    state.templates = templates
    state.programs = programs
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
    state.error = t('store.settings_not_saved', { error: (error as Error).message })
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

/** The interface's language (null: the browser's): applied at once; saved, then everything read
 * again, so that the server's messages already shown (DCS problems, errors) speak it too. The pages
 * do not change: they speak the commands' language. */
async function setUiLanguage(ui_language: string | null): Promise<void> {
  setLanguage(ui_language)
  changeSettings({ ui_language })
  await flushSettings()
  await load()
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

/** Hidden in every module, by name: a vJoy, a device unplugged for good */
function isHidden(name: string): boolean {
  const wanted = name.toLowerCase()
  return !!state.settings?.hidden_devices.some((d) => d.toLowerCase() === wanted)
}

/** Devices listed for the current module: the hidden ones only when asked */
const devices = computed(() => orderedDevices(profile.value).filter((d) => state.showHidden || !isHidden(d.name)))
const hiddenCount = computed(() => (profile.value?.devices ?? []).filter((d) => isHidden(d.name)).length)

/** Every device name seen in the modules, with the number of modules it is configured in */
const allDevices = computed(() => {
  const count = new Map<string, number>()
  for (const p of profiles.value) for (const name of new Set(p.devices.map((d) => d.name))) count.set(name, (count.get(name) ?? 0) + 1)
  return [...count].map(([name, modules]) => ({ name, modules })).sort((a, b) => a.name.localeCompare(b.name))
})

function setHidden(name: string, hidden: boolean): void {
  if (!state.settings) return
  const others = state.settings.hidden_devices.filter((d) => d.toLowerCase() !== name.toLowerCase())
  changeSettings({ hidden_devices: hidden ? [...others, name] : others })
}
const device = computed<Device | null>(() => devices.value.find((d) => d.full_name === state.deviceKey) ?? null)

function isExported(profileName: string, d: Device): boolean {
  if (isHidden(d.name)) return false
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

/** Back to the template the device's name matches: forget the choice made by hand */
function resetTemplate(d: Device): void {
  if (!state.settings || state.settings.device_templates[d.name] === undefined) return
  const device_templates = { ...state.settings.device_templates }
  delete device_templates[d.name]
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

// --- other programs ------------------------------------------------------------------------

/** SRS profile of a DCS module: the user's choice, else the one matched by name (null: none) */
function srsProfileFor(profileName: string): string | null {
  const chosen = state.settings?.srs_profiles[profileName]
  const known = state.programs?.srs.profiles ?? []
  if (chosen !== undefined && (chosen === '' || known.includes(chosen))) return chosen || null
  return state.programs?.srs.matched[profileName] ?? null
}

function setSrsProfile(profileName: string, srsProfile: string | null | undefined): void {
  if (!state.settings) return
  const srs_profiles = { ...state.settings.srs_profiles }
  if (srsProfile === undefined) delete srs_profiles[profileName]
  else srs_profiles[profileName] = srsProfile ?? ''
  changeSettings({ srs_profiles })
}

/** Other programs' buttons read in a module: its SRS profile's, VectorXR's */
function readProgramBindings(profileName: string): ProgramBinding[] {
  const srs = srsProfileFor(profileName)
  return [...(srs ? (state.programs?.srs.bindings[srs] ?? []) : []), ...(state.programs?.vectorxr.bindings ?? [])]
}

/** Every other program's button in a module: read, then entered by hand */
function programBindings(profileName: string): ProgramBinding[] {
  return [...readProgramBindings(profileName), ...(state.settings?.program_bindings ?? [])]
}

/** Every program known: read (SRS when found, VectorXR when it binds something) and by hand */
const programNames = computed(() => {
  const names = new Set<string>()
  if (state.programs?.srs.profiles.length) names.add(SRS)
  for (const b of state.programs?.vectorxr.bindings ?? []) names.add(b.program)
  for (const b of state.settings?.program_bindings ?? []) names.add(b.program)
  return [...names].sort((a, b) => a.localeCompare(b))
})

const styles = computed(() => programStyles(programNames.value, state.settings?.program_colors ?? {}))

function isProgramShown(program: string): boolean {
  return !state.settings?.hidden_programs.includes(program)
}

function setProgramShown(program: string, shown: boolean): void {
  if (!state.settings) return
  const others = state.settings.hidden_programs.filter((p) => p !== program)
  changeSettings({ hidden_programs: shown ? others : [...others, program] })
}

function setProgramColor(program: string, color: string): void {
  if (!state.settings) return
  changeSettings({ program_colors: { ...state.settings.program_colors, [program]: color } })
}

function setManualBindings(program_bindings: ManualProgramBinding[]): void {
  changeSettings({ program_bindings })
}

/** SRS's folder changed: read the programs again */
async function saveSrsDir(srs_dir: string | null): Promise<void> {
  if (!state.settings) return
  clearTimeout(saveTimer)
  await flushSettings()
  const saved = await api.saveSettings({ srs_dir })
  state.settings = saved.settings
  state.programs = await api.programs(pageLanguage(state.dcs?.language))
}

/** The name a module shows (DCS's), its folder name staying the key of everything */
function profileLabel(profileName: string): string {
  return profiles.value.find((p) => p.name === profileName)?.display_name || profileName
}

async function pagesOf(profileName: string, d: Device): Promise<Page[]> {
  const id = templateIdFor(d)
  const [m, template] = await Promise.all([getMeasurer(), id ? loadTemplate(id) : Promise.resolve(null)])
  const marks = marksFor(d.guid, programBindings(profileName), state.settings?.hidden_programs ?? [])
  return devicePages(
    {
      profile: profileLabel(profileName),
      device: d,
      template,
      measurer: m,
      fontCss: FONT_CSS,
      programs: { marks, styles: styles.value },
      lang: pageLanguage(state.dcs?.language),
    },
    state.settings?.layer_mode ?? 'merge',
    state.settings?.split_wide ?? true,
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
    profileLabel,
    devices,
    device,
    hiddenCount,
    allDevices,
    isHidden,
    setHidden,
    load,
    changeSettings,
    flushSettings,
    saveReading,
    setUiLanguage,
    orderedDevices,
    isExported,
    templateIdFor,
    toggleExported,
    setTemplate,
    resetTemplate,
    moveDevice,
    pagesOf,
    modulePages,
    srsProfileFor,
    setSrsProfile,
    readProgramBindings,
    programBindings,
    programNames,
    programStyles: styles,
    isProgramShown,
    setProgramShown,
    setProgramColor,
    setManualBindings,
    saveSrsDir,
  }
}
