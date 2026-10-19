// Shapes of the server's JSON (hotas_kneeboard/app.py)

export interface Label {
  text: string
  pressed: string[]
  released: string[]
}

/** input (JOY_BTN14) -> layer ("" = base, "Paddle", "JOY_BTN5 + Paddle") -> label */
export type Inputs = Record<string, Record<string, Label>>

export interface Device {
  full_name: string
  name: string
  guid: string
  source: 'effective' | 'diff'
  error: string | null
  layers: string[]
  binding_count: number
  inputs: Inputs
  auto_template_id: string | null
  dcs_disabled: boolean // listed in DCS's Config/Input/disabled.lua
  inactive_modifiers: string[] // modifiers of its layers DCS drops: their device was renamed
}

export interface Profile {
  name: string // the folder in Saved Games\DCS\Config\Input: the key of settings and kneeboard files
  display_name: string // what DCS shows in its controls screen ("AH-64D Pilot"), else the folder
  unit_type: string | null
  found: boolean
  devices: Device[]
}

export interface BindingsResponse {
  profiles: Profile[]
  error: string | null
}

export type Box = [number, number, number, number]

export interface TemplateInput {
  box: Box
  more_boxes?: Box[]
  anchor?: [number, number] | null
}

export interface Credits {
  author?: string
  source?: string
  license?: string
}

export interface TemplateSummary {
  id: string
  name: string
  devices: string[]
  size: [number, number]
  credits: Credits
  /** numbering checked on the real device, else null (a converted template as drawn) */
  checked: { by: string; date: string } | null
  /** in the user's folder: can be changed in place, deleted */
  user: boolean
  /** a user's version in front of a bundled template of the same id (list only) */
  replaces_bundled?: boolean
}

export interface Template extends TemplateSummary {
  image: string
  inputs: Record<string, TemplateInput>
  /** vertical lines where the drawing is cut into kneeboard pages (a wide throttle) */
  split_at?: number[]
}

export type LayerMode = 'merge' | 'split'

export interface Settings {
  dcs_install_dir: string | null
  saved_games_dir: string | null
  language: string | null
  exported: Record<string, Record<string, boolean>>
  device_templates: Record<string, string>
  device_order: Record<string, string[]>
  /** device names (without GUID) hidden in every module */
  hidden_devices: string[]
  buttonless_devices: string[] // names without GUID: axes only (pedals), their generic buttons removable
  layer_mode: LayerMode
  page_height: number
  /** drawings whose template has a cut line (split_at) become several pages */
  split_wide: boolean
  /** SRS install folder; null: found in the registry */
  srs_dir: string | null
  /** DCS profile -> SRS profile chosen by the user ("" = none); not listed: matched by name */
  srs_profiles: Record<string, string>
  /** buttons of other programs entered by hand */
  program_bindings: ManualProgramBinding[]
  /** programs not shown on the pages */
  hidden_programs: string[]
  /** program -> colour, #rrggbb */
  program_colors: Record<string, string>
}

/** A button another program uses: device by its GUID (lower case, no braces), input in DCS's names */
export interface ProgramBinding {
  program: string
  device_guid: string
  input: string
  action: string
}

export interface ManualProgramBinding extends ProgramBinding {
  /** shown in the list when the device is not plugged */
  device_name: string
}

export interface ProgramsResponse {
  srs: {
    /** where the SRS profiles were found; null: SRS not found */
    folder: string | null
    profiles: string[]
    /** DCS profile -> SRS profile matched by name (else SRS's default profile) */
    matched: Record<string, string | null>
    bindings: Record<string, ProgramBinding[]>
  }
  vectorxr: { file: string | null; bindings: ProgramBinding[] }
  problems: string[]
}

export interface DcsState {
  install_dir: string | null
  install_detected: boolean
  saved_games_dir: string | null
  saved_games_detected: boolean
  language: string
  problems: string[]
}

export interface StateResponse {
  version: string
  settings_file: string
  dcs: DcsState
  settings: Settings
}

export interface KneeboardResult {
  folder: string
  written: string[]
  removed: string[]
}

/** A zip of Saved Games/DCS/Config/Input, made before each change the app makes to DCS's files */
export interface DcsBackup {
  id: string
  created: string // ISO, local time
  reason: string
  size: number
  files: number
}

export interface DcsDevicesResponse {
  disabled: string[] // full names, as in disabled.lua
  seen: string[] // devices DCS created in its last two sessions (Logs/dcs.log, dcs.log.old)
  absent: { device: string; profiles: string[] }[] // devices with diffs DCS did not see
  log_date: string | null // when DCS last wrote dcs.log
}

/** A modifier DCS drops because its device was renamed by its driver (same GUID, new name) */
export interface ModifierIssue {
  profile: string
  modifier: string
  key: string | null
  device: string // the name in modifiers.lua
  new_device: string | null // the name DCS logged; null when it cannot be fixed
  problem: string | null
}

export interface ModifiersResponse {
  issues: ModifierIssue[]
  deleted: { profile: string; backup: string; created: string }[] // modifiers.lua gone, held by a backup
}

export interface ModifiersFixed {
  fixed: { profile: string; modifier: string; device: string; new_device: string }[]
  backup: DcsBackup
}

/** A device whose hat carries some of the 8 generic views ("View Up slow"…) of DCS's defaults */
export interface HatViewsDevice {
  device: string // full name, with its GUID
  hat_only_views: boolean // the user placed nothing on its hat, in any module: offered by default
  own_hat: { profile: string; key: string; command: string }[] // a few of the hat bindings the user placed
  own_hat_count: number
  modules: {
    profile: string
    unit_type: string | null
    file: string // the diff file's device name
    views: string[] // keys of the views to remove (JOY_BTN_POV1_U…)
    new_file: boolean // no diff there yet: one is created
    error: string | null // left out
  }[]
}

export interface HatViewsPreview {
  all_modules: boolean
  devices: HatViewsDevice[]
}

export interface HatViewsResult {
  backup: DcsBackup
  written: { profile: string; device: string; removed: number; expected: number; deleted: boolean; created: boolean }[]
  differences: string[] // what the bindings read again say differently from the preview
}

export interface DcsBackupsResponse {
  folder: string
  dcs_running: boolean | null // null: could not be checked
  backups: DcsBackup[]
}

/** One binding of a device in a module, as DCS's files name it (GET /api/dcs-config/bindings) */
export interface BindingRef {
  kind: 'key' | 'axis'
  hash: string // the command's, as DCS hashes it
  key: string // JOY_BTN1, JOY_X…
  reformers: string[] // the modifiers held with it
}

export interface DeviceBinding extends BindingRef {
  command: string // translated as the game shows it
  category: string | null
  // placed by the user; by the module for this very device; by the module's profile of any joystick
  origin: 'user' | 'device' | 'generic'
  removable: boolean // false: an engine command whose number is unknown, its removal cannot be written
}

export interface DeviceBindingsResponse {
  profile: string
  device: string
  editable: boolean // false for a module not installed: nothing to compute the diff from
  bindings: DeviceBinding[]
}

export interface BindingsRemoved {
  backup: DcsBackup
  removed: number
  asked: number
}

/** The buttons DCS gives a device marked as having none (GET /api/dcs-config/generic-buttons) */
export interface GenericButtonsDevice {
  device: string // full name, with its GUID
  name: string
  modules: {
    profile: string
    unit_type: string | null
    file: string
    bindings: { hash: string; key: string; reformers: string[]; command: string }[]
    unknown: { key: string; command: string }[] // generic too, but not removable (engine command number unknown)
    new_file: boolean
    error: string | null
  }[]
}

export interface GenericButtonsPreview {
  all_modules: boolean
  marked: string[]
  devices: GenericButtonsDevice[]
}
