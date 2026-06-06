import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  BEHAVIOR_IMPORT_ENDPOINT,
  behaviorFusionCopy,
  extractBehaviorImportError,
  importBehaviorDayFile,
  normalizeBehaviorImportResponse,
} from '../src/utils/lifestyleBehaviorImport.js'

const viewSource = readFileSync(new URL('../src/views/LifestyleView.vue', import.meta.url), 'utf8')

const uploadedBehaviorDay = {
  schema_version: 'behavior_day_scenario.v1',
  scenario_id: 'uploaded_2026-05-13_patient_a',
  patient_id: 'patient_a',
  local_date: '2026-05-13',
  title: 'Uploaded behavior day',
  data_mode: 'user_uploaded',
  timeline: [
    {
      schema_version: 'behavior_timeline_event.v1',
      event_id: 'evt_0700_breakfast',
      time: '07:00',
      event_type: 'diet_vision',
      label: 'Breakfast',
      data_mode: 'user_uploaded',
      payload: {
        nutrition: { calories: 420, carbs: 48, protein: 18, fat: 14, sodium_mg: 480 },
        vision_provenance: { source_type: 'user_uploaded' },
      },
      source_provenance: { source_type: 'user_uploaded' },
    },
  ],
  lifestyle_context: {
    schema_version: 'lifestyle_context.v1',
    data_mode: 'user_uploaded',
    scenario_id: 'uploaded_2026-05-13_patient_a',
    summary: { steps: 7600 },
    source_provenance: { source_type: 'user_uploaded' },
  },
  source_provenance: { source_type: 'user_uploaded' },
}

const contractResponse = {
  status: 'success',
  import: {
    schema_version: 'platform_behavior_day_import_result.v1',
    data_mode: 'user_uploaded',
    source_format: 'csv',
    filename: 'patient-day.csv',
    validation: { event_count: 1, warnings: [] },
    source_provenance: {
      source_type: 'user_uploaded',
      source_label: 'uploaded_csv',
      source_format: 'csv',
      artifact_schema: 'platform_behavior_day_csv.v1',
      filename: 'patient-day.csv',
    },
  },
  behavior_day: uploadedBehaviorDay,
}

test('behavior import posts multipart file to the frozen parse-only endpoint and returns contract behavior_day', async () => {
  let postedUrl = ''
  let postedPayload
  let committedScenario = null
  const file = new File(['patient_id,local_date,time,event_type\npatient_a,2026-05-13,07:00,sleep'], 'day.csv', {
    type: 'text/csv',
  })
  const axiosClient = {
    async post(url, payload) {
      postedUrl = url
      postedPayload = payload
      return { data: contractResponse }
    },
  }

  const result = await importBehaviorDayFile({
    axiosClient,
    file,
    onSuccess: (scenario) => {
      committedScenario = scenario
    },
  })

  assert.equal(postedUrl, BEHAVIOR_IMPORT_ENDPOINT)
  assert.equal(postedPayload.get('file'), file)
  assert.equal(result.ok, true)
  assert.equal(result.scenario, uploadedBehaviorDay)
  assert.equal(result.scenario.data_mode, 'user_uploaded')
  assert.equal(result.scenario.lifestyle_context.data_mode, 'user_uploaded')
  assert.equal(committedScenario, result.scenario)
})

test('behavior import still tolerates legacy scenario envelope while normalizing to uploaded behavior day', () => {
  const scenario = normalizeBehaviorImportResponse({ scenario: uploadedBehaviorDay })

  assert.equal(scenario, uploadedBehaviorDay)
  assert.equal(scenario.data_mode, 'user_uploaded')
})

test('behavior import failure preserves the previous selected scenario by not committing success', async () => {
  const previousScenario = { scenario_id: 'metabolic_day_001', data_mode: 'simulated_demo' }
  let selectedScenario = previousScenario
  const axiosClient = {
    async post() {
      const error = new Error('bad upload')
      error.response = { data: { detail: 'CSV must contain one patient and one local_date' } }
      throw error
    },
  }

  const result = await importBehaviorDayFile({
    axiosClient,
    file: new File(['bad'], 'bad.csv', { type: 'text/csv' }),
    onSuccess: (scenario) => {
      selectedScenario = scenario
    },
  })

  assert.equal(result.ok, false)
  assert.equal(result.error, 'CSV must contain one patient and one local_date')
  assert.equal(selectedScenario, previousScenario)
})

test('structured 413 upload error includes message and file detail path', () => {
  const error = {
    response: {
      status: 413,
      data: {
        status: 'error',
        error: {
          code: 'file_too_large',
          message: '上传文件过大',
          details: [
            { path: 'file', code: 'max_size', message: '最大支持 1 MB' },
          ],
        },
      },
    },
  }

  assert.equal(extractBehaviorImportError(error), '上传文件过大：file: 最大支持 1 MB')
})

test('structured 415 upload error includes unsupported file type detail', () => {
  const error = {
    response: {
      status: 415,
      data: {
        status: 'error',
        error: {
          code: 'unsupported_media_type',
          message: '不支持的文件类型',
          details: [
            { path: 'file', code: 'unsupported_extension', message: '仅支持 .csv 或 .json' },
          ],
        },
      },
    },
  }

  assert.equal(extractBehaviorImportError(error), '不支持的文件类型：file: 仅支持 .csv 或 .json')
})

test('structured selector mismatch error includes each detail path', () => {
  const error = {
    response: {
      status: 400,
      data: {
        status: 'error',
        error: {
          code: 'selector_mismatch',
          message: '上传参数与文件内容不一致',
          details: [
            { path: 'patient_id', code: 'mismatch', message: '请求 patient_b 与文件 patient_a 不一致' },
            { path: 'local_date', code: 'mismatch', message: '请求 2026-05-14 与文件 2026-05-13 不一致' },
          ],
        },
      },
    },
  }

  assert.equal(
    extractBehaviorImportError(error),
    '上传参数与文件内容不一致：patient_id: 请求 patient_b 与文件 patient_a 不一致；local_date: 请求 2026-05-14 与文件 2026-05-13 不一致'
  )
})

test('behavior import rejects non uploaded provenance from response', () => {
  assert.throws(
    () => normalizeBehaviorImportResponse({
      ...contractResponse,
      behavior_day: { ...uploadedBehaviorDay, data_mode: 'real_device' },
    }),
    /user_uploaded/
  )
})

test('helper strings and lifestyle view assertions stay readable Chinese', () => {
  assert.equal(behaviorFusionCopy(uploadedBehaviorDay), '使用上传数据生成风险解释')
  assert.equal(behaviorFusionCopy({ data_mode: 'simulated_demo' }), '使用当前行为数据生成风险解释')
  assert.match(viewSource, /用户上传数据/)
  assert.match(viewSource, /物联网实时监测（蓝牙）/)
  assert.match(viewSource, /当前设备数据不会写入行为时间线/)
})

test('lifestyle view exposes upload-first labels without duplicate real-device placeholder', () => {
  assert.match(viewSource, /data-testid="behavior-day-timeline"/)
  assert.match(viewSource, /data-testid="behavior-upload-import"/)
  assert.match(viewSource, /accept="\.csv,\.json,application\/json,text\/csv"/)
  assert.match(viewSource, /handleBehaviorImport/)
  assert.match(viewSource, /一天行为时间线/)
  assert.match(viewSource, /等待上传/)
  assert.match(viewSource, /disabled/)
  assert.match(viewSource, /displayDataMode\('user_uploaded'\)/)
  assert.match(viewSource, /behaviorFusionCopy\(selectedScenario\)/)
  assert.doesNotMatch(viewSource, /真实设备接口/)
  assert.doesNotMatch(viewSource, /设备同步暂未开放/)
  assert.doesNotMatch(viewSource, /演示患者一天时间线/)
  assert.doesNotMatch(viewSource, /加载演示患者/)
  assert.doesNotMatch(viewSource, /仅用于演示/)
  assert.doesNotMatch(viewSource, /行为模拟器/)
})

test('fusion analysis uses returned user_uploaded lifestyle_context without persistence or device sync claims', () => {
  assert.match(viewSource, /runScenarioFusionAnalysis/)
  assert.match(viewSource, /lifestyle_context:\s*selectedScenario\.value\.lifestyle_context/)
  assert.match(viewSource, /behaviorFusionCopy\(selectedScenario\.value\)/)
  assert.match(viewSource, /axios\.post\('\/analyze\/comprehensive',\s*payload\)/)
  assert.doesNotMatch(viewSource, /\/api\/v1\/iot\/sync\/batch['"`],\s*selectedScenario/)
  assert.doesNotMatch(viewSource, /saveProfileToCloud\(\)/)
}
)
