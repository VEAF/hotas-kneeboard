import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextFree } from '../catalog'
import { detectInput, hatDirection } from '../gamepad'
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

  it('keeps where the draft is saved out of the history', () => {
    addInput('JOY_BTN1', [50, 50])
    editor.draft!.id = 'my-icp' // saved meanwhile
    undo()
    expect(editor.draft!.id).toBe('my-icp')
  })

  it('makes a new template when starting from the template of another device', async () => {
    const { fromTemplate } = await import('../state')
    const warthog = {
      id: 'thrustmaster-warthog-throttle',
      name: 'Warthog',
      devices: ['Throttle - HOTAS Warthog'],
      size: [10, 10] as [number, number],
      credits: {},
      checked: { by: 'David', date: '2026-10-19' },
      user: false,
      image: 'background.svg',
      inputs: {},
    }
    expect(fromTemplate(warthog, 'data:', false, 'VPC Stick MT-50CM3')).toMatchObject({
      id: null,
      overrides: false,
      checked: null, // checked on another device
      name: 'VPC Stick MT-50CM3',
      devices: ['VPC Stick MT-50CM3'],
    })
    // a template naming no device (found by choosing it by hand): fixed in place, learns the name
    expect(fromTemplate({ ...warthog, devices: [] }, 'data:', false, 'VPC Stick MT-50CM3')).toMatchObject({
      id: 'thrustmaster-warthog-throttle',
      overrides: true,
      devices: ['VPC Stick MT-50CM3'],
    })
    // the device's own template: fixing it, in front of the bundled one
    expect(fromTemplate(warthog, 'data:', false, 'Throttle - HOTAS Warthog')).toMatchObject({
      id: 'thrustmaster-warthog-throttle',
      overrides: true,
      checked: { by: 'David', date: '2026-10-19' },
    })
  })

  it('adds, undoes and keeps a cut line', async () => {
    const { toggleSplit } = await import('../state')
    toggleSplit()
    expect(editor.draft!.split_at).toEqual([200])
    undo()
    expect(editor.draft!.split_at).toEqual([])
    redo()
    expect(draftTemplate(editor.draft!).split_at).toEqual([200])
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
  // hats are known per device id from one listening to the next: a test about hats names its own
  const pad = (pressed: number[], axes = [0, 0, 0], id = 'WINWING ICP (Vendor: 4098)'): Gamepad =>
    ({
      index: 0,
      id,
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

  it('reports a hat, given as the axis after the eight DCS axes', async () => {
    const released = [0, 0, 0, 0, 0, 0, 0, 0, 0, 3.29] // Chrome and Firefox: index 9, out of [-1, 1]
    pads = [pad([], released, 'hat 1')]
    const found = detectInput(new AbortController().signal)
    pads = [pad([], [...released.slice(0, 9), 3 / 7], 'hat 1')] // -1 + 2/7 × 5: down-left
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN_POV1_DL' })
  })

  it('hears again a button or a hat held when listening started, once released', async () => {
    // the check listens again right after a press, the finger still on it
    const hat = (v: number) => [0, 0, 0, 0, 0, 0, 0, 0, 0, v]
    pads = [pad([5], hat(-1), 'hat 2')]
    const found = detectInput(new AbortController().signal)
    pads = [pad([], hat(3.29), 'hat 2')]
    await vi.advanceTimersByTimeAsync(50)
    pads = [pad([], hat(3 / 7), 'hat 2')]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN_POV1_DL' })

    pads = [pad([5], hat(3.29), 'hat 2')]
    const again = detectInput(new AbortController().signal)
    pads = [pad([], hat(3.29), 'hat 2')]
    await vi.advanceTimersByTimeAsync(50)
    pads = [pad([5], hat(3.29), 'hat 2')]
    await vi.advanceTimersByTimeAsync(50)
    await expect(again).resolves.toMatchObject({ key: 'JOY_BTN6' })
  })

  it('hears a hat moved from one direction to another without a stop in the middle', async () => {
    const hat = (v: number) => [0, 0, 0, 0, 0, 0, 0, 0, 0, v]
    const before = new AbortController()
    pads = [pad([], hat(3.29), 'hat 3')] // seen released once: a hat
    const first = detectInput(before.signal)
    before.abort()
    await expect(first).rejects.toMatchObject({ name: 'AbortError' })
    pads = [pad([], hat(5 / 7), 'hat 3')] // left, held when listening started again
    const found = detectInput(new AbortController().signal)
    await vi.advanceTimersByTimeAsync(50)
    pads = [pad([], hat(-3 / 7), 'hat 3')] // straight to right
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN_POV1_R' })
  })

  it('does not take a ninth axis that wanders for a hat', async () => {
    const axes = (v: number) => [0, 0, 0, 0, 0, 0, 0, 0, v]
    pads = [pad([], axes(0.1), 'nine axes')]
    const found = detectInput(new AbortController().signal)
    pads = [pad([], axes(-0.2), 'nine axes')] // "DR" then "D" if it were a hat
    await vi.advanceTimersByTimeAsync(50)
    pads = [pad([3], axes(-0.2), 'nine axes')]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN4' })
  })

  it('reads the eight directions of a hat, and none when released', () => {
    expect([-1, -5 / 7, -3 / 7, -1 / 7, 1 / 7, 3 / 7, 5 / 7, 1].map(hatDirection)).toEqual([
      'U', 'UR', 'R', 'DR', 'D', 'DL', 'L', 'UL',
    ])
    expect(hatDirection(3.29)).toBeNull()
    expect(hatDirection(1.29)).toBeNull()
  })

  it('waits for a second press on a device that just appeared', async () => {
    // the press that wakes the device up is not known: a held switch may look pressed too
    pads = []
    const notices: string[] = []
    const found = detectInput(new AbortController().signal, (n) => notices.push(n))
    pads = [pad([0, 7])]
    await vi.advanceTimersByTimeAsync(50)
    expect(notices).toEqual(['WINWING ICP (Vendor: 4098)'])
    pads = [pad([0, 7, 3])]
    await vi.advanceTimersByTimeAsync(50)
    await expect(found).resolves.toMatchObject({ key: 'JOY_BTN4' })
  })

  it('stops when asked', async () => {
    pads = [pad([])]
    const controller = new AbortController()
    const found = detectInput(controller.signal)
    controller.abort()
    await expect(found).rejects.toMatchObject({ name: 'AbortError' })
  })
})
