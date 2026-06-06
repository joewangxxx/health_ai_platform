export const BEHAVIOR_IMPORT_ENDPOINT = '/api/v1/lifestyle/import-behavior-day'

export const normalizeBehaviorImportResponse = (responseData) => {
  if (responseData?.status && responseData.status !== 'success') {
    throw new Error(responseData.message || '行为数据上传解析失败')
  }

  const scenario = responseData?.behavior_day || responseData?.scenario || responseData?.data?.scenario
  if (!scenario || typeof scenario !== 'object') {
    throw new Error('上传响应缺少行为时间线')
  }
  if (scenario.data_mode !== 'user_uploaded') {
    throw new Error('上传行为数据必须标记为 user_uploaded')
  }
  if (scenario.lifestyle_context?.data_mode !== 'user_uploaded') {
    throw new Error('上传生活方式上下文必须标记为 user_uploaded')
  }
  return scenario
}

const formatStructuredErrorDetails = (details) => {
  if (!Array.isArray(details)) return ''
  return details
    .map((detail) => {
      if (!detail || typeof detail !== 'object') return ''
      const message = detail.message || detail.code || ''
      if (!message) return ''
      return detail.path ? `${detail.path}: ${message}` : message
    })
    .filter(Boolean)
    .join('；')
}

export const extractBehaviorImportError = (error) => {
  const structuredError = error?.response?.data?.error
  if (structuredError?.message) {
    const detailText = formatStructuredErrorDetails(structuredError.details)
    return detailText ? `${structuredError.message}：${detailText}` : structuredError.message
  }

  return (
    error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || '行为数据上传解析失败'
  )
}

export const importBehaviorDayFile = async ({ axiosClient, file, onSuccess }) => {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await axiosClient.post(BEHAVIOR_IMPORT_ENDPOINT, formData)
    const scenario = normalizeBehaviorImportResponse(response.data)
    onSuccess?.(scenario)
    return { ok: true, scenario }
  } catch (error) {
    return { ok: false, error: extractBehaviorImportError(error) }
  }
}

export const behaviorFusionCopy = (scenario) => {
  if (scenario?.data_mode === 'user_uploaded') {
    return '使用上传数据生成风险解释'
  }
  return '使用当前行为数据生成风险解释'
}
