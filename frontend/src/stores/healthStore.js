import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useHealthStore = defineStore('health', () => {
    // 1. User Profile (Clinical Data)
    const userProfile = ref({
        // Default initialized to null to trigger empty state in UI
        Age: null,
        Gender: null,
        Height: null, // cm
        Weight: null, // kg
        BMI: null,
        WaistCircum: null,
        SBP: null,
        DBP: null,
        Glucose_Fasting: null,
        HbA1c: null,
        Cholesterol_Total: null,
        Triglycerides: null,
        Cholesterol_HDL: null,
        Sleep_Hours: null,
        eGFR: null,
        ALT: null,
        // 🔥 New V10 Biomarkers
        WBC: null,
        GGT: null,
        ALP: null,
        Platelet: null,
        // Task 73: Extra unstructured data
        extra_data: {}
    })

    // 2. Genomics Data
    const geneData = ref(null)
    const geneStats = ref({ loaded: false, count: 0 })
    const genePreviewList = ref([])  // V5: 用于表格展示的完整SNP列表

    // 3. IoT Data
    const iotData = ref({ hr: 0, steps: 0 })
    const deviceStatus = ref("等待连接")

    // 4. Activity State
    const activityState = ref({
        carbs: 0,
        activity_type: 'rest',
        current_hr: 70
    })

    // 5. Diet Nutrition (from food vision)
    const dietNutrition = ref({
        calories: 0,
        carbs: 0,
        protein: 0,
        fat: 0
    })

    // 6. Results
    const riskReport = ref(null)
    const analysisContext = ref(null)

    // --- Actions ---
    function updateProfile(newProfile) {
        userProfile.value = { ...userProfile.value, ...newProfile }
    }

    function setGeneData(data, count = 0, previewList = []) {
        geneData.value = data
        geneStats.value = { loaded: true, count }
        genePreviewList.value = previewList  // V5: Store preview list
    }

    function updateIoT(data) {
        if ('hr' in data) iotData.value.hr = data.hr
        if ('steps' in data) iotData.value.steps = data.steps
        deviceStatus.value = "设备在线"
    }

    function setRiskReport(data) {
        riskReport.value = data
    }

    function normalizeFieldStateSummary(summary) {
        const source = summary && typeof summary === 'object' ? summary : {}
        return {
            recognized: Array.isArray(source.recognized) ? source.recognized : [],
            derived: Array.isArray(source.derived) ? source.derived : [],
            missing: Array.isArray(source.missing) ? source.missing : [],
            user_confirmed: Array.isArray(source.user_confirmed) ? source.user_confirmed : [],
            user_entered: Array.isArray(source.user_entered) ? source.user_entered : [],
        }
    }

    function normalizeAnalysisContext(context) {
        if (!context || typeof context !== 'object' || Array.isArray(context)) {
            return null
        }

        return {
            ...context,
            schema_version: context.schema_version || 'analysis_context.v1',
            analysis_mode: context.analysis_mode || 'final',
            provisional_reasons: Array.isArray(context.provisional_reasons) ? context.provisional_reasons : [],
            blocking_fields: Array.isArray(context.blocking_fields) ? context.blocking_fields : [],
            field_state_summary: normalizeFieldStateSummary(context.field_state_summary),
        }
    }

    function normalizeDocumentImport(data) {
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            return null
        }

        const normalized = { ...data }

        if (normalized.ocr_processing_status && typeof normalized.ocr_processing_status === 'object') {
            normalized.ocr_processing_status = {
                schema_version: normalized.ocr_processing_status.schema_version || 'ocr_processing_status.v1',
                ...normalized.ocr_processing_status,
            }
        }

        if (normalized.analysis_context) {
            normalized.analysis_context = normalizeAnalysisContext(normalized.analysis_context)
        }

        return normalized
    }

    function isCanonicalRiskSnapshot(data) {
        return Boolean(
            data &&
            typeof data === 'object' &&
            !Array.isArray(data) &&
            data.schema_version === 'risk_snapshot.v1' &&
            Array.isArray(data.findings)
        )
    }

    async function fetchLatestRiskReport(profileOverride = userProfile.value) {
        const cleanClinical = Object.fromEntries(
            Object.entries(profileOverride || {}).filter(([key, value]) => {
                if (value === null || value === undefined || value === '') return false
                return key !== 'risk_history' && key !== 'genomic_data' && key !== 'user'
            })
        )

        if (!Object.keys(cleanClinical).length) {
            return false
        }

        try {
            const res = await axios.post('/analyze/comprehensive', {
                clinical: cleanClinical,
                user_snps: geneData.value || {}
            })

            if (res.data.analysis_context) {
                analysisContext.value = normalizeAnalysisContext(res.data.analysis_context)
            }

            if (res.data.status === 'success' && res.data.risk_report) {
                riskReport.value = res.data.risk_report
                return true
            }
        } catch (e) {
            console.error('Failed to refresh backend-owned risk report:', e)
        }

        return false
    }

    function setDietNutrition(data) {
        if (data) {
            dietNutrition.value = {
                calories: data.calories || 0,
                carbs: data.carbs || 0,
                protein: data.protein || 0,
                fat: data.fat || 0
            }
        }
    }

    async function fetchIoTData() {
        try {
            // Note: In real app this might use the auth header, 
            // but the backend endpoint seems public or we rely on global defaults
            const res = await axios.get('/api/device/current')
            updateIoT(res.data)
        } catch (e) {
            deviceStatus.value = "设备离线"
        }
    }

    // 🔥 V7: 从云端拉取用户档案
    async function fetchRemoteProfile() {
        try {
            const res = await axios.get('/user/profile')
            if (res.data.status === 'success' && res.data.profile) {
                const profile = res.data.profile

                // 同步临床数据
                updateProfile(profile)

                // 同步基因数据
                if (profile.genomic_data) {
                    const genomicObj = typeof profile.genomic_data === 'string'
                        ? JSON.parse(profile.genomic_data)
                        : profile.genomic_data
                    geneData.value = genomicObj
                    geneStats.value = { loaded: true, count: Object.keys(genomicObj).length }
                }

                // 同步历史风险报告
                if (profile.risk_history) {
                    const historyObj = typeof profile.risk_history === 'string'
                        ? JSON.parse(profile.risk_history)
                        : profile.risk_history
                    if (isCanonicalRiskSnapshot(historyObj)) {
                        riskReport.value = null
                        await fetchLatestRiskReport(profile)
                    } else {
                        riskReport.value = historyObj
                    }
                }

                console.log('✅ 用户档案已从云端同步')
                return true
            }
        } catch (e) {
            console.error('拉取云端档案失败:', e)
        }
        return false
    }

    // 🔥 V7: 保存档案到云端
    async function saveProfileToCloud() {
        try {
            const payload = {
                ...userProfile.value,
                user_snps: geneData.value,
                risk_report: riskReport.value
            }

            const res = await axios.post('/user/profile', payload)
            if (res.data.status === 'success') {
                console.log('✅ 档案已云端同步')
                return true
            }
        } catch (e) {
            console.error('保存云端档案失败:', e)
        }
        return false
    }

    // 🔥 Task 59: 历史数据导入
    const importData = ref(null)

    function setImportData(data) {
        importData.value = normalizeDocumentImport(data)
        analysisContext.value = importData.value?.analysis_context || null
        console.log('📥 Import data set:', data)
    }

    function clearImportData() {
        importData.value = null
        analysisContext.value = null
    }

    return {
        userProfile,
        geneData,
        geneStats,
        genePreviewList,  // V5: Export preview list
        iotData,
        deviceStatus, // Make sure to export this
        activityState,
        dietNutrition,  // V6: 4D Nutrition data
        riskReport,
        analysisContext,
        importData,        // Task 59
        updateProfile,
        setGeneData,
        updateIoT,
        setRiskReport,
        setDietNutrition,  // V6: Set diet nutrition
        fetchIoTData,
        fetchLatestRiskReport,
        fetchRemoteProfile,   // V7: Fetch from cloud
        saveProfileToCloud,   // V7: Save to cloud
        setImportData,        // Task 59
        clearImportData       // Task 59
    }
})

