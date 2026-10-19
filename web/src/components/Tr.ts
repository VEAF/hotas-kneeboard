// A translated text with markup in it: `<Tr k="key"><template #path><code>…</code></template></Tr>`
// puts each slot where the catalog's text says `{path}`, so a translation may move it; the other
// placeholders come from `params`, as with t(); `n` picks the plural form, as tn() does.

import { defineComponent, Fragment, h, type PropType } from 'vue'
import { pluralKey, t } from '../lib/i18n'

export default defineComponent({
  name: 'Tr',
  props: {
    k: { type: String, required: true },
    params: { type: Object as PropType<Record<string, unknown>>, default: undefined },
    /** a count: the key's `.one` or `.other` form, `{n}` in the text */
    n: { type: Number, default: undefined },
  },
  setup(props, { slots }) {
    return () => {
      const key = props.n === undefined ? props.k : pluralKey(props.k, props.n)
      const parts = t(key, props.n === undefined ? props.params : { ...props.params, n: props.n }).split(/\{(\w+)\}/)
      return h(
        Fragment,
        parts.map((part, i) => (i % 2 ? (slots[part]?.() ?? `{${part}}`) : part)),
      )
    }
  },
})
