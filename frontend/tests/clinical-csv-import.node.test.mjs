import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/views/ClinicalView.vue', import.meta.url), 'utf8')

test('clinical view places CSV import beside OCR using direct file input triggers', () => {
  const ocrIndex = source.indexOf('data-testid="ocr-upload"')
  const csvIndex = source.indexOf('data-testid="csv-upload"')

  assert.notEqual(ocrIndex, -1, 'OCR upload control should exist')
  assert.notEqual(csvIndex, -1, 'CSV upload control should exist')
  assert.ok(csvIndex > ocrIndex, 'CSV import should be placed after the OCR upload control')

  const headerControls = source.slice(ocrIndex, csvIndex + 900)
  assert.match(headerControls, /data-testid="ocr-file-input"/)
  assert.match(headerControls, /@change="handleOcrFileSelection"/)
  assert.match(headerControls, /<GlassButton\s+size="sm"\s+:loading="ocrLoading"\s+@click="triggerOcrFileInput"/)
  assert.match(headerControls, /data-testid="csv-file-input"/)
  assert.match(headerControls, /@change="handleCsvFileSelection"/)
  assert.match(headerControls, /<GlassButton\s+size="sm"\s+:loading="csvImportLoading"\s+@click="triggerCsvFileInput"/)
  assert.match(headerControls, /CSV/)
  assert.match(headerControls, /accept="\.csv"/)
})

test('clinical upload buttons directly trigger hidden file inputs', () => {
  assert.match(source, /const\s+triggerOcrFileInput\s*=\s*\(\)\s*=>\s*\{[\s\S]*ocrFileInput\.value\?\.click\(\)/)
  assert.match(source, /const\s+triggerCsvFileInput\s*=\s*\(\)\s*=>\s*\{[\s\S]*csvFileInput\.value\?\.click\(\)/)
  assert.match(source, /const\s+handleOcrFileSelection\s*=\s*async\s*\(event\)/)
  assert.match(source, /const\s+handleCsvFileSelection\s*=\s*async\s*\(event\)/)
})

test('clinical CSV import posts multipart file to the frozen parse-only endpoint', () => {
  assert.match(source, /const\s+handleCsvImport\s*=\s*async\s*\(uploadFile\)/)
  assert.match(source, /formData\.append\('file',\s*uploadFile\.raw\)/)
  assert.match(source, /axios\.post\('\/api\/v1\/profile\/import-csv',\s*formData/)
  assert.match(source, /'Content-Type':\s*'multipart\/form-data'/)
  const handlerStart = source.indexOf('const handleCsvImport = async (uploadFile)')
  const handlerEnd = source.indexOf('const handleClearAll', handlerStart)
  const handlerSource = source.slice(handlerStart, handlerEnd)
  assert.doesNotMatch(handlerSource, /saveProfileToCloud\(/)
})

test('clinical CSV import fills profile from response profile and keeps backend errors visible', () => {
  assert.match(source, /const\s+importedProfile\s*=\s*res\.profile/)
  assert.match(source, /applyOcrDataToProfile\(importedProfile,\s*\{\s*overwrite:\s*true/)
  assert.match(source, /CSV/)
  assert.match(source, /e\.response\?\.data\?\.detail/)
})

test('clinical inputs keep a white data-entry surface in the dark app shell', () => {
  const styleStart = source.indexOf('<style scoped>')
  const styleSource = source.slice(styleStart)

  assert.match(styleSource, /\.clinical-form\s+:deep\(\.el-input__wrapper\),/)
  assert.match(styleSource, /background-color:\s*rgba\(255,\s*255,\s*255,\s*0\.92\)\s*!important/)
  assert.doesNotMatch(styleSource, /\.dark\s+\.clinical-form\s+:deep\(\.el-input__wrapper\)\s*\{[^}]*rgba\(0,\s*0,\s*0,\s*0\.3\)/s)
})
