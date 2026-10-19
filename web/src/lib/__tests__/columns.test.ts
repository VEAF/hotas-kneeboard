import { describe, expect, it } from 'vitest'
import { clampColumn, COLUMN_MAX, COLUMN_MIN } from '../columns'

describe('clampColumn', () => {
  it('keeps a width between the bounds', () => {
    expect(clampColumn(260.4, 1920)).toBe(260)
    expect(clampColumn(20, 1920)).toBe(COLUMN_MIN)
    expect(clampColumn(2000, 1920)).toBe(COLUMN_MAX)
  })

  it('leaves the page at least a third of a narrow window', () => {
    expect(clampColumn(500, 1200)).toBe(400)
  })
})
