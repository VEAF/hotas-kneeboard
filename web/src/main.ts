import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'
import '@fontsource/barlow/400.css'
import '@fontsource/barlow/500.css'
import '@fontsource/barlow/600.css'
import '@fontsource/barlow-condensed/500.css'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import 'primeicons/primeicons.css'
import './style.css'
import App from './App.vue'

// Aura with the amber of a cockpit caution light as primary colour
const Cockpit = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#fff8eb',
      100: '#feecc7',
      200: '#fdd78a',
      300: '#fbbd4d',
      400: '#f0a83a',
      500: '#e08e14',
      600: '#c46a0c',
      700: '#a24d0e',
      800: '#843d13',
      900: '#6c3313',
      950: '#3e1905',
    },
  },
})

createApp(App)
  .use(PrimeVue, { theme: { preset: Cockpit, options: { darkModeSelector: '.app-dark' } }, ripple: false })
  .use(ToastService)
  .directive('tooltip', Tooltip)
  .mount('#app')
