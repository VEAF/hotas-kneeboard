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
}

export interface Profile {
  name: string
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
  seen: string[] // devices DCS created at its last start (Logs/dcs.log)
}

export interface DcsBackupsResponse {
  folder: string
  dcs_running: boolean | null // null: could not be checked
  backups: DcsBackup[]
}
