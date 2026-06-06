const trimTrailingSlash = (value) => value.replace(/\/+$/, '')

const normalizePath = (path) => (path.startsWith('/') ? path : `/${path}`)

export const DEFAULT_DEV_API_BASE_URL = 'http://127.0.0.1:8000'

export const resolveApiBaseUrl = (env = {}) => {
    const explicitBaseUrl = trimTrailingSlash((env?.VITE_API_BASE_URL || '').trim())
    if (explicitBaseUrl) return explicitBaseUrl
    if (env?.DEV && !env?.PROD) return DEFAULT_DEV_API_BASE_URL
    return ''
}

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env)

export const apiUrl = (path = '') => {
    if (!path) return API_BASE_URL || '/'
    if (/^https?:\/\//i.test(path)) return path
    return API_BASE_URL ? `${API_BASE_URL}${normalizePath(path)}` : normalizePath(path)
}
