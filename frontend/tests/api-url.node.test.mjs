import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveApiBaseUrl } from '../src/utils/api.js'

test('uses local FastAPI backend by default in Vite dev mode', () => {
  assert.equal(resolveApiBaseUrl({ DEV: true }), 'http://127.0.0.1:8000')
})

test('keeps production same-origin when no API base URL is configured', () => {
  assert.equal(resolveApiBaseUrl({ PROD: true, MODE: 'production' }), '')
})

test('uses explicit API base URL without trailing slashes', () => {
  assert.equal(
    resolveApiBaseUrl({ VITE_API_BASE_URL: 'http://localhost:9000///', DEV: true }),
    'http://localhost:9000'
  )
})
