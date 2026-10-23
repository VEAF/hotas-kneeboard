// "Press the button to identify it": the browser's Gamepad API reports the devices the system
// sees as game controllers. Its button index i is taken as DCS's JOY_BTN(i+1) and its axes in
// DirectInput order; both are a guess to check on each device, manual entry stays the reference.
// A hat comes as one more axis after those (index 9 in Chrome and Firefox on Windows, measured on
// the Orion JGRIP-F16 in Firefox): -1 up, then 2/7 per eighth clockwise, a value out of [-1, 1]
// when released. It is taken as hat 1.

import { AXES } from './catalog'
import { t } from '../lib/i18n'

export interface Detected {
  key: string
  /** the browser's name of the device, e.g. "WINWING ICP (Vendor: 4098 Product: bf06)" */
  device: string
}

const PRESSED = 0.5
const AXIS_MOVE = 0.5
const HAT_DIRECTIONS = ['U', 'UR', 'R', 'DR', 'D', 'DL', 'L', 'UL']

/** The direction of a hat reported as an axis value, or null when it is released */
export function hatDirection(value: number): string | null {
  if (!(Math.abs(value) <= 1.05)) return null
  return HAT_DIRECTIONS[Math.round(((value + 1) * 7) / 2) % 8]
}

interface Baseline {
  buttons: boolean[]
  axes: number[]
}

export function gamepadSupported(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.getGamepads === 'function'
}

/** First input that moves on any device, compared with its state when listening started.
 * A device the browser had not shown yet appears on its first press; its state then becomes its
 * reference (a switch held on a throttle would look pressed), `onAppear` tells to press again. */
export function detectInput(signal: AbortSignal, onAppear?: (device: string) => void): Promise<Detected> {
  return new Promise((resolve, reject) => {
    if (!gamepadSupported()) {
      reject(new Error(t('editor.no_gamepad_api')))
      return
    }
    const baselines = new Map<string, Baseline>()
    const keyOf = (pad: Gamepad) => `${pad.index}|${pad.id}`
    for (const pad of navigator.getGamepads()) {
      if (pad) baselines.set(keyOf(pad), { buttons: pad.buttons.map((b) => b.value > PRESSED), axes: [...pad.axes] })
    }
    let frame = 0
    const stop = () => cancelAnimationFrame(frame)
    signal.addEventListener('abort', () => {
      stop()
      reject(new DOMException('listening stopped', 'AbortError'))
    })
    const poll = () => {
      for (const pad of navigator.getGamepads()) {
        if (!pad) continue
        const known = baselines.get(keyOf(pad))
        if (!known) {
          baselines.set(keyOf(pad), { buttons: pad.buttons.map((b) => b.value > PRESSED), axes: [...pad.axes] })
          onAppear?.(pad.id)
          continue
        }
        const base = known
        const button = pad.buttons.findIndex((b, i) => b.value > PRESSED && !base.buttons[i])
        if (button !== -1) {
          stop()
          resolve({ key: `JOY_BTN${button + 1}`, device: pad.id })
          return
        }
        const axis = pad.axes.findIndex((v, i) => Math.abs(v - (base.axes[i] ?? 0)) > AXIS_MOVE)
        if (axis !== -1 && axis < AXES.length) {
          stop()
          resolve({ key: AXES[axis], device: pad.id })
          return
        }
        const hat = pad.axes.findIndex(
          (v, i) => i >= AXES.length && hatDirection(v) !== null && hatDirection(base.axes[i] ?? 2) === null,
        )
        if (hat !== -1) {
          stop()
          resolve({ key: `JOY_BTN_POV1_${hatDirection(pad.axes[hat])}`, device: pad.id })
          return
        }
      }
      frame = requestAnimationFrame(poll)
    }
    frame = requestAnimationFrame(poll)
  })
}
