import { describe, expect, it } from 'vitest'
import { docUrl } from '../docs'

describe('docUrl', () => {
  it('opens the documentation of the running version', () => {
    expect(docUrl('0.1.0')).toBe('https://veaf.github.io/hotas-kneeboard/0.1.0/')
  })

  it('opens the site while the version is not known', () => {
    expect(docUrl('')).toBe('https://veaf.github.io/hotas-kneeboard/')
    expect(docUrl('0.2.0.dev1')).toBe('https://veaf.github.io/hotas-kneeboard/')
  })
})
