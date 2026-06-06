import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/layout/MainLayout.vue', import.meta.url), 'utf8')

test('main layout does not let the desktop sidebar squeeze mobile content', () => {
  assert.match(source, /class="app-sidebar/)
  assert.match(source, /@media\s*\(max-width:\s*768px\)/)
  assert.match(source, /\.app-sidebar\s*\{[\s\S]*display:\s*none/)
  assert.match(source, /\.app-main\s*:deep\(\.el-main__content\)|\.app-main/)
})
