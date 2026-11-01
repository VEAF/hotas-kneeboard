import { describe, expect, it } from 'vitest'
import { DCS_KNEEBOARD_RATIO, fitPage } from '../export'
import type { Page } from '../page'

const page = (width: number, height: number): Page => ({ title: '', width, height, svg: '' })

describe('kneeboard pictures', () => {
  it('fits a landscape page across the frame, centred in height', () => {
    const height = 1024
    const width = height * DCS_KNEEBOARD_RATIO
    const at = fitPage(page(1417, 1024), width, height)
    expect(at.x).toBe(0)
    expect(at.width).toBeCloseTo(width)
    expect(at.height / at.width).toBeCloseTo(1024 / 1417) // not distorted
    expect(at.y).toBeCloseTo((height - at.height) / 2)
  })

  it('fits a page narrower than the frame in its height, centred in width', () => {
    const at = fitPage(page(600, 1000), 700, 1000)
    expect(at).toEqual({ x: 50, y: 0, width: 600, height: 1000 })
  })
})
