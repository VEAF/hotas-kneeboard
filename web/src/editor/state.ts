// The template being edited, its selection and its undo/redo history.

import { computed, reactive } from 'vue'
import type { Box, Credits, Template, TemplateInput } from '../lib/types'
import { nextFree } from './catalog'

export interface Draft {
  /** id it is saved under: a user template it replaces, a bundled one it overrides; null = new */
  id: string | null
  /** started from a bundled template: saving puts the user's version in front of it */
  overrides: boolean
  name: string
  devices: string[]
  size: [number, number]
  image: { dataUrl: string; name: string } | null
  inputs: Record<string, TemplateInput>
  credits: Credits
}

/** Selected part: the label box (index 0 = box, 1.. = more_boxes) or the marker of an input */
export interface Selection {
  key: string
  part: 'box' | 'anchor'
  index: number
}

// where the draft is saved (id, overrides) is not part of the history: undoing a change made
// before a save must not make the next save create another template
type Snapshot = Omit<Draft, 'id' | 'overrides'>

const HISTORY_LIMIT = 200
export const DEFAULT_BOX: [number, number] = [120, 24]

export const editor = reactive({
  draft: null as Draft | null,
  selection: null as Selection | null,
  dirty: false,
  zoom: 1,
  undo: [] as Snapshot[],
  redo: [] as Snapshot[],
  /** device the editor was opened for: its bindings for the preview, and the template given to it */
  forDevice: null as { profile: string; deviceKey: string; name: string } | null,
})

function snapshot(draft: Draft): Snapshot {
  const { id: _, overrides: __, ...rest } = draft
  // the picture (a long data: URL) is shared, not copied: it is never changed in place
  return { ...rest, devices: [...draft.devices], inputs: JSON.parse(JSON.stringify(draft.inputs)) }
}

export function newDraft(fields: Partial<Draft> = {}): Draft {
  return {
    id: null,
    overrides: false,
    name: '',
    devices: [],
    size: [800, 600],
    image: null,
    inputs: {},
    credits: {},
    ...fields,
  }
}

export function open(draft: Draft): void {
  editor.draft = draft
  editor.selection = null
  editor.dirty = false
  editor.undo = []
  editor.redo = []
}

/** A draft from a template. For a device the template is not made for (chosen by hand, or a
 * starting point), the draft is a new template for that device: saving it must not change the
 * template of another device. */
export function fromTemplate(template: Template, image: string, user: boolean, forDevice?: string): Draft {
  const extension = template.image.split('.').pop() ?? 'png'
  const copy = !!forDevice && !template.devices.some((d) => d.toLowerCase() === forDevice.toLowerCase())
  return newDraft({
    id: copy ? null : template.id,
    overrides: !copy && !user,
    name: copy ? forDevice : template.name,
    devices: copy ? [forDevice] : [...template.devices],
    size: [...template.size],
    image: { dataUrl: image, name: `background.${extension}` },
    inputs: JSON.parse(JSON.stringify(template.inputs)),
    credits: { ...template.credits },
  })
}

/** Call before a change: it can then be undone */
export function remember(): void {
  if (!editor.draft) return
  editor.undo.push(snapshot(editor.draft))
  if (editor.undo.length > HISTORY_LIMIT) editor.undo.shift()
  editor.redo = []
  editor.dirty = true
}

function restore(from: Snapshot[], to: Snapshot[]): void {
  if (!editor.draft || !from.length) return
  to.push(snapshot(editor.draft))
  editor.draft = { ...from.pop()!, id: editor.draft.id, overrides: editor.draft.overrides }
  editor.dirty = true
  if (editor.selection && !(editor.selection.key in editor.draft.inputs)) editor.selection = null
}

export const undo = () => restore(editor.undo, editor.redo)
export const redo = () => restore(editor.redo, editor.undo)
export const canUndo = computed(() => editor.undo.length > 0)
export const canRedo = computed(() => editor.redo.length > 0)

// --- changes -------------------------------------------------------------------------------

export function addInput(key: string | null, anchor: [number, number]): string {
  const draft = editor.draft!
  remember()
  const used = Object.keys(draft.inputs)
  const chosen = key && !(key in draft.inputs) ? key : nextFree(used, editor.selection?.key)
  const [w, h] = DEFAULT_BOX
  // the box beside the marker, on the side with room
  const right = anchor[0] + 30 + w <= draft.size[0]
  const x = right ? anchor[0] + 30 : Math.max(0, anchor[0] - 30 - w)
  const y = Math.min(Math.max(0, anchor[1] - h / 2), draft.size[1] - h)
  draft.inputs[chosen] = { box: [round(x), round(y), w, h], anchor: [round(anchor[0]), round(anchor[1])] }
  editor.selection = { key: chosen, part: 'box', index: 0 }
  return chosen
}

export function removeSelected(): void {
  const draft = editor.draft
  const sel = editor.selection
  if (!draft || !sel || !(sel.key in draft.inputs)) return
  remember()
  const input = draft.inputs[sel.key]
  if (sel.part === 'box' && sel.index > 0) {
    input.more_boxes = (input.more_boxes ?? []).filter((_, i) => i !== sel.index - 1)
    if (!input.more_boxes.length) delete input.more_boxes
    editor.selection = { key: sel.key, part: 'box', index: 0 }
  } else if (sel.part === 'anchor') {
    delete input.anchor
    editor.selection = { key: sel.key, part: 'box', index: 0 }
  } else {
    delete draft.inputs[sel.key]
    editor.selection = null
  }
}

/** A copy of the selected input on the next free input, a little lower */
export function duplicateSelected(): void {
  const draft = editor.draft
  const sel = editor.selection
  if (!draft || !sel || !(sel.key in draft.inputs)) return
  remember()
  const source = draft.inputs[sel.key]
  const key = nextFree(Object.keys(draft.inputs), sel.key)
  const dy = source.box[3] + 6
  draft.inputs[key] = {
    box: [source.box[0], Math.min(source.box[1] + dy, draft.size[1] - source.box[3]), source.box[2], source.box[3]],
    ...(source.anchor ? { anchor: [source.anchor[0], Math.min(source.anchor[1] + dy, draft.size[1])] } : {}),
  }
  editor.selection = { key, part: 'box', index: 0 }
}

export function renameSelected(newKey: string): void {
  const draft = editor.draft
  const sel = editor.selection
  if (!draft || !sel || newKey === sel.key || !(sel.key in draft.inputs)) return
  remember()
  const moved = draft.inputs[sel.key]
  const other = draft.inputs[newKey]
  delete draft.inputs[sel.key]
  // the input already placed elsewhere swaps with this one: nothing is lost
  if (other) draft.inputs[sel.key] = other
  draft.inputs[newKey] = moved
  editor.selection = { ...sel, key: newKey }
}

export function boxOf(sel: Selection): Box | null {
  const input = editor.draft?.inputs[sel.key]
  if (!input) return null
  return sel.index === 0 ? input.box : (input.more_boxes?.[sel.index - 1] ?? null)
}

export function setBox(sel: Selection, box: Box): void {
  const input = editor.draft?.inputs[sel.key]
  if (!input) return
  const clean = box.map(round) as Box
  if (sel.index === 0) input.box = clean
  else if (input.more_boxes) input.more_boxes[sel.index - 1] = clean
}

export function nudgeSelected(dx: number, dy: number): void {
  const sel = editor.selection
  const draft = editor.draft
  if (!sel || !draft) return
  const input = draft.inputs[sel.key]
  if (!input) return
  remember()
  if (sel.part === 'anchor' && input.anchor) {
    input.anchor = [clamp(input.anchor[0] + dx, 0, draft.size[0]), clamp(input.anchor[1] + dy, 0, draft.size[1])]
  } else {
    const box = boxOf(sel)
    if (box) setBox(sel, [clamp(box[0] + dx, 0, draft.size[0] - box[2]), clamp(box[1] + dy, 0, draft.size[1] - box[3]), box[2], box[3]])
  }
}

export function addExtraBox(): void {
  const sel = editor.selection
  const input = sel && editor.draft?.inputs[sel.key]
  if (!sel || !input) return
  remember()
  const [x, y, w, h] = input.box
  input.more_boxes = [...(input.more_boxes ?? []), [x + 20, y + h + 8, w, h]]
  editor.selection = { key: sel.key, part: 'box', index: input.more_boxes.length }
}

export function toggleAnchor(): void {
  const sel = editor.selection
  const input = sel && editor.draft?.inputs[sel.key]
  if (!sel || !input) return
  remember()
  if (input.anchor) {
    delete input.anchor
  } else {
    const [x, y, , h] = input.box
    input.anchor = [Math.max(0, x - 30), y + h / 2]
  }
  editor.selection = { key: sel.key, part: input.anchor ? 'anchor' : 'box', index: 0 }
}

export function round(v: number): number {
  return Math.round(v * 10) / 10
}

export function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), max)
}

/** The draft as a template, for the page renderer (preview) and for saving */
export function draftTemplate(draft: Draft): Template {
  return {
    id: draft.id ?? 'draft',
    name: draft.name || 'Nouveau gabarit',
    devices: draft.devices,
    size: draft.size,
    credits: draft.credits,
    image: draft.image?.name ?? 'background.png',
    user: true,
    inputs: draft.inputs,
  }
}
