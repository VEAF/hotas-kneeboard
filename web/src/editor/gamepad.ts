// "Press the button to identify it": the browser's Gamepad API reports the devices the system
// sees as game controllers. Its button index i is taken as DCS's JOY_BTN(i+1) and its axes in
// DirectInput order; both are a guess to check on each device, manual entry stays the reference.
// Hats are not reported the same way by every browser: they are left to manual entry.

import { AXES } from './catalog'

export interface Detected {
  key: string
  /** the browser's name of the device, e.g. "WINWING ICP (Vendor: 4098 Product: bf06)" */
  device: string
}

const PRESSED = 0.5
const AXIS_MOVE = 0.5

interface Baseline {
  buttons: boolean[]
  axes: number[]
}

export function gamepadSupported(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.getGamepads === 'function'
}

/** First input that moves on any device, compared with its state when listening started.
 * A device the browser had not shown yet appears on its first press: what is pressed then counts. */
export function detectInput(signal: AbortSignal): Promise<Detected> {
  return new Promise((resolve, reject) => {
    if (!gamepadSupported()) {
      reject(new Error("Ce navigateur ne donne pas accès aux manettes (Gamepad API)."))
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
      reject(new DOMException('écoute arrêtée', 'AbortError'))
    })
    const poll = () => {
      for (const pad of navigator.getGamepads()) {
        if (!pad) continue
        const known = baselines.get(keyOf(pad))
        const base: Baseline = known ?? { buttons: pad.buttons.map(() => false), axes: pad.axes.map(() => 0) }
        const button = pad.buttons.findIndex((b, i) => b.value > PRESSED && !base.buttons[i])
        if (button !== -1) {
          stop()
          resolve({ key: `JOY_BTN${button + 1}`, device: pad.id })
          return
        }
        // a new device's axes start wherever they rest: only a known device's axes count
        const axis = known ? pad.axes.findIndex((v, i) => Math.abs(v - (base.axes[i] ?? 0)) > AXIS_MOVE) : -1
        if (axis !== -1 && axis < AXES.length) {
          stop()
          resolve({ key: AXES[axis], device: pad.id })
          return
        }
        if (!known) baselines.set(keyOf(pad), { buttons: pad.buttons.map((b) => b.value > PRESSED), axes: [...pad.axes] })
      }
      frame = requestAnimationFrame(poll)
    }
    frame = requestAnimationFrame(poll)
  })
}
