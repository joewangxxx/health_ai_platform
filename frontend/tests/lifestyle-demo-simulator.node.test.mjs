import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const viewSource = readFileSync(new URL('../src/views/LifestyleView.vue', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../src/stores/healthStore.js', import.meta.url), 'utf8')

test('lifestyle view keeps sample scenario APIs as code fallback without exposing the old patient loader UI', () => {
  assert.match(viewSource, /fetchBehaviorScenarios/)
  assert.match(viewSource, /axios\.get\('\/api\/v1\/demo\/behavior-scenarios'\)/)
  assert.match(viewSource, /loadBehaviorScenario/)
  assert.match(viewSource, /axios\.get\(`\/api\/v1\/demo\/behavior-scenarios\/\$\{scenarioId\}`\)/)
  assert.doesNotMatch(viewSource, /v-model="selectedScenarioId"/)
  assert.doesNotMatch(viewSource, /加载演示患者/)
  assert.doesNotMatch(viewSource, /fetchBehaviorScenarios\(\)\s*\n\s*\}/)
})

test('lifestyle upload timeline exposes replay controls, progress, selected event details, and upload provenance', () => {
  assert.match(viewSource, /data-testid="behavior-day-timeline"/)
  assert.match(viewSource, /data-testid="behavior-play-toggle"/)
  assert.match(viewSource, /data-testid="behavior-replay"/)
  assert.match(viewSource, /data-testid="behavior-progress"/)
  assert.match(viewSource, /selectedEvent/)
  assert.match(viewSource, /user_uploaded/)
  assert.match(viewSource, /等待上传/)
  assert.match(viewSource, /displayScenarioTitle/)
  assert.match(viewSource, /displayEventLabel/)
  assert.match(viewSource, /displayPayloadKey/)
  assert.doesNotMatch(viewSource, /class="demo-scenario-select"/)
  assert.doesNotMatch(viewSource, /演示患者一天时间线/)
  assert.doesNotMatch(viewSource, /行为模拟器/)
  assert.match(viewSource, /metric-chip-label/)
  assert.match(viewSource, /formatMetricNumber/)
})

test('diet vision demo event updates nutrition including sodium while retaining provenance', () => {
  assert.match(viewSource, /applyDietVisionEvent/)
  assert.match(viewSource, /nutrition\.sodium_mg/)
  assert.match(viewSource, /vision_provenance/)
  assert.match(storeSource, /sodium_mg:\s*0/)
  assert.match(storeSource, /provenance:\s*null/)
})

test('demo fusion analysis submits clinical data, gene data, and scenario lifestyle_context explicitly', () => {
  assert.match(viewSource, /runDemoFusionAnalysis/)
  assert.match(viewSource, /lifestyle_context:\s*selectedScenario\.value\.lifestyle_context/)
  assert.match(viewSource, /user_snps:\s*geneData\.value\s*\|\|\s*\{\}/)
  assert.match(viewSource, /axios\.post\('\/analyze\/comprehensive',\s*payload\)/)
  assert.doesNotMatch(viewSource, /saveProfileToCloud\(\)/)
  assert.doesNotMatch(viewSource, /\/api\/v1\/iot\/sync\/batch['"`],\s*selectedScenario/)
})

test('demo fusion analysis sends only approved clinical fields and omits empty clinical payloads', () => {
  assert.match(viewSource, /CLINICAL_ANALYSIS_FIELDS/)
  assert.match(viewSource, /CLINICAL_ANALYSIS_FIELDS\.has\(key\)/)
  assert.match(viewSource, /if\s*\(Object\.keys\(cleanClinical\)\.length\)\s*\{\s*payload\.clinical\s*=\s*cleanClinical/s)
  assert.doesNotMatch(viewSource, /clinical:\s*cleanClinical/)
  assert.doesNotMatch(viewSource, /id['"`]?\s*,\s*['"`]?user_id/)
  assert.doesNotMatch(viewSource, /allow_research['"`]?\s*,\s*['"`]?clinical/)
})
