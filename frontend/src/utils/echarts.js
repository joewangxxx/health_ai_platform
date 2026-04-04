import * as echarts from 'echarts/core'

const registeredModules = new Set()

export function ensureEChartsModules(modules) {
  const freshModules = modules.filter((module) => !registeredModules.has(module))

  if (freshModules.length > 0) {
    echarts.use(freshModules)
    freshModules.forEach((module) => registeredModules.add(module))
  }

  return echarts
}

export { echarts }
export default echarts
