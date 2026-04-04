const trimTrailingSlash = (value) => value.replace(/\/+$/, '')

const normalizePath = (path) => (path.startsWith('/') ? path : `/${path}`)

export const API_BASE_URL = trimTrailingSlash(
    (import.meta.env.VITE_API_BASE_URL || '').trim()
)

export const apiUrl = (path = '') => {
    if (!path) return API_BASE_URL || '/'
    if (/^https?:\/\//i.test(path)) return path
    return API_BASE_URL ? `${API_BASE_URL}${normalizePath(path)}` : normalizePath(path)
}
