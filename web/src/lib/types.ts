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
}

export type LayerMode = 'merge' | 'split'

export interface Settings {
  dcs_install_dir: string | null
  saved_games_dir: string | null
  language: string | null
  exported: Record<string, Record<string, boolean>>
  device_templates: Record<string, string>
  device_order: Record<string, string[]>
  layer_mode: LayerMode
  page_height: number
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
  dcs: DcsState
  settings: Settings
}

export interface KneeboardResult {
  folder: string
  written: string[]
  removed: string[]
}
