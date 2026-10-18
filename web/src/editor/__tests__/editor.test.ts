import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextFree } from '../catalog'
import { detectInput } from '../gamepad'
import {
  addExtraBox,
  addInput,
  draftTemplate,
  duplicateSelected,
  editor,
  newDraft,
  nudgeSelected,
  open,
  redo,
  removeSelected,
  renameSelected,
  toggleAnchor,
  undo,
} from '../state'

beforeEach(() => open(newDraft({ name: 'ICP', size: [400, 300] })))

describe('editor state', () => {
  it('places an input beside its marker, on the next free input', () => {
    const key = addInput(null, [100, 100])
    expect(key).toBe('JOY_BTN1')
    expect(editor.draft!.inputs.JOY_BTN1).toEqual({ box: [130, 88, 120, 24], anchor: [100, 100] })
    // near the right edge the box goes to the left of the marker
    addInput(null, [390, 150])
    expect(editor.draft!.inputs.JOY_BTN2.box[0]).toBe(240)
    expect(editor.dirty).toBe(true)
  })

  it('undoes and redoes every change', () => {
    addInput('JOY_BTN5', [50, 50])
    nudgeSelected(10, 0)
    expect(editor.draft!.inputs.JOY_BTN5.box[0]).toBe(90)
    undo()
    expect(editor.draft!.inputs.JOY_BTN5.box[0]).toBe(80)
    undo()
    expect(editor.draft!.inputs).toEqual({})
    redo()
    redo()
    expect(editor.draft!.inputs.JOY_BTN5.box[0]).toBe(90)
  })

  it('keeps boxes and markers on the picture when nudged', () => {
    addInput('JOY_BTN1', [10, 10])
    nudgeSelected(-1000, -1000)
    expect(editor.draft!.inputs.JOY_BTN1.box.slice(0, 2)).toEqual([0, 0])
    editor.selection = { key: 'JOY_BTN1', part: 'anchor', index: 0 }
    nudgeSelected(1000, 1000)
    expect(editor.draft!.inputs.JOY_BTN1.anchor).toEqual([400, 300])
  })

  it('duplicates on the next button, a little lower', () => {
    addInput('JOY_BTN3', [50, 50])
    duplicateSelected()
    expect(editor.selection!.key).toBe('JOY_BTN4')
    expect(editor.draft!.inputs.JOY_BTN4.box[1]).toBe(editor.draft!.inputs.JOY_BTN3.box[1] + 30)
  })

  it('swaps two inputs when one takes the input of the other', () => {
    addInput('JOY_BTN1', [50, 50])
    addInput('JOY_BTN2', [50, 150])
    renameSelected('JOY_BTN1')
    expect(editor.draft!.inputs.JOY_BTN1.anchor).toEqual([50, 150])
    expect(editor.draft!.inputs.JOY_BTN2.anchor).toEqual([50, 50])
  })

  it('removes a second box, a marker, then the input', () => {
    addInput('JOY_BTN1', [50, 50])
    addExtraBox()
    expect(editor.draft!.inputs.JOY_BTN1.more_boxes).toHaveLength(1)
    removeSelected() // the second box is selected
    expect(editor.draft!.inputs.JOY_BTN1.more_boxes).toBeUndefined()
    toggleAnchor() // remove the marker
    expect(editor.draft!.inputs.JOY_BTN1.anchor).toBeUndefined()
    removeSelected()
    expect(editor.draft!.inputs).toEqual({})
  })

  it('gives the renderer and the server a template', () => {
    addInput('JOY_X', [50, 50])
    const t = draftTemplate(editor.draft!)
    expect(t).toMatchObject({ name: 'ICP', size: [400, 300], inputs: { JOY_X: { anchor: [50, 50] } } })
  })

  it('finds the next free input in catalog order', () => {
    expect(nextFree(['JOY_BTN1', 'JOY_BTN2'])).toBe('JOY_BTN3')
    expect(nextFree(['JOY_BTN1'], 'JOY_BTN127')).toBe('JOY_BTN128')
    expect(nextFree([], 'JOY_BTN128')).toBe('JOY_BTN_POV1_U')
  })
})

describe('gamepad', () => {
  let pads: (Gamepad | null)[] = []
  const pad = (pressed: number[], axes = [0, 0, 0]): Gamepad =>
    ({
      index: 0,
      id: 'WINWING ICP (Vendor: 4098)',
      buttons: Array.from({ length: 20 }, (_, i) => ({ pressed: pressed.includes(i), value: pressed.includes(i) ? 1 : 0, touched: false })),
      axes,
    }) as unknown as Gamepad

  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => setTimeout(() => cb(0), 16) as unknown as number)
    vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id))
    Object.defineProperty(navigator, 'getGamepads', { value: () => pads, configurable: true })
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reports the button pressed after listening started, as DCS numbers it', async () => {
    pads = [pad([2])] // held before: ignored
    const found = detectInput(new AbortController().signal)
    pads = [pad([2, 13])]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toEqual({ key: 'JOY_BTN14', device: 'WINWING ICP (Vendor: 4098)' })
  })

  it('reports a moved axis', async () => {
    pads = [pad([])]
    const found = detectInput(new AbortController().signal)
    pads = [pad([], [0, 0, 0.9])]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_Z' })
  })

  it('takes the press that makes a device appear', async () => {
    pads = []
    const found = detectInput(new AbortController().signal)
    pads = [pad([0])]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN1' })
  })

  it('stops when asked', async () => {
    pads = [pad([])]
    const controller = new AbortController()
    const found = detectInput(controller.signal)
    controller.abort()
    await expect(found).rejects.toMatchObject({ name: 'AbortError' })
  })
})
