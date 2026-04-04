import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('element-plus/es/components/')) {
              const componentMatch = id.match(/element-plus\/es\/components\/([^/]+)/)
              if (componentMatch?.[1]) {
                return `element-plus-${componentMatch[1]}`
              }
            }
            if (id.includes('element-plus')) {
              return 'element-plus'
            }
            if (id.includes('@element-plus/icons-vue')) {
              return 'element-plus-icons'
            }
            if (id.includes('lucide-vue-next')) {
              return 'lucide-icons'
            }
            if (id.includes('axios')) {
              return 'axios'
            }
            if (id.includes('motion')) {
              return 'motion'
            }
            if (id.includes('zrender')) {
              return 'echarts-zrender'
            }
            if (id.includes('echarts/core') || id.includes('echarts/lib/core')) {
              return 'echarts-core'
            }
            if (id.includes('echarts/components') || id.includes('echarts/lib/component')) {
              return 'echarts-components'
            }
            if (id.includes('echarts/charts') || id.includes('echarts/lib/chart')) {
              return 'echarts-charts'
            }
            if (id.includes('echarts')) {
              return 'echarts'
            }
            if (id.includes('markdown-it')) {
              return 'markdown'
            }
            if (
              id.includes('/vue/') ||
              id.includes('vue-router') ||
              id.includes('/pinia/')
            ) {
              return 'vue-core'
            }
            return 'vendor'
          }
        },
      },
    },
  },
})
