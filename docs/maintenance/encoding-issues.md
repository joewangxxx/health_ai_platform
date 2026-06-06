# Encoding Issue Inventory

Generated on: 2026-04-24

Scope: scan text-like files for non-UTF-8 decoding failures, GBK-to-UTF-8 recoverable mojibake lines, and lossy CJK lines that contain replacement/question-mark artifacts. This is an inventory only; no source code was deleted or rewritten.

## Phase 2 Remediation Note

On 2026-04-24, a focused Phase 2 remediation repaired confirmed high-confidence mojibake in `backend/main.py`, `backend/services/chat_service.py`, and `tests/test_chat_agent_service.py`, then added `tests/test_encoding_hygiene.py` as a regression guard. The table below remains the original Phase 1 inventory snapshot and is not rewritten retroactively.

## Summary

- Files with suspected encoding issues: 25
- High-severity entries: 7
- Medium-severity entries: 18

## Recommended Handling Rules

- Do not run blind global replacement across code.
- Prefer regenerating generated reports from fixed scripts when possible.
- For user-facing Chinese text, restore the intended UTF-8 wording manually and verify UI/build behavior.
- For comments/docstrings, repair only when context is clear; otherwise mark as review-needed.
- `manual_review` means the line contains lossy mixed text that cannot be safely auto-repaired.

## Findings

| Severity | Path | Decode status | Recoverable lines | Lossy marker lines | Suggested action | Sample / repair preview |
| --- | --- | --- | --- | --- | --- | --- |
| high | backend/services/ocr_service.py | utf-8 | 0 | 17 | manual_restore_or_regenerate_from_source | L231: `('BMI', r'(?:\bBMI\b\|体重指数\|体质指数)\D{0,10}(\d{2}\.\d{1,2}\|\d{2})', 1),` -> `manual_review`<br>L232: `('WBC', r'(?:\bWBC\b\|白细胞(?:计数)?)\D{0,10}(\d{1,2}\.?\d{0,2})', 1),` -> `manual_review`<br>L233: `('HGB', r'(?:\bHGB\b\|血红蛋白)\D{0,10}(\d{2,3}\.?\d{0,2})', 1),` -> `manual_review` |
| high | frontend/src/views/ProfileView.vue | utf-8 | 0 | 14 | manual_restore_or_regenerate_from_source | L22: `{{ authStore.user?.username \|\| '加载中...' }}` -> `manual_review`<br>L25: `{{ authStore.user?.email \|\| '未设置邮箱' }}` -> `manual_review`<br>L28: `{{ authStore.user?.is_superuser ? '管理员' : '普通用户' }}` -> `manual_review` |
| high | backend/main.py | utf-8 | 4 | 9 | manual_restore_or_regenerate_from_source | L312: `raise HTTPException(status_code=400, detail="鐢ㄦ埛鍚嶅凡瀛樺湪 (Username already taken)")` -> `raise HTTPException(status_code=400, detail="用户名已存在 (Username already taken)")`<br>L318: `raise HTTPException(status_code=400, detail="璇ラ偖绠卞凡琚敞鍐?(Email already registered)")` -> `manual_review`<br>L322: `raise HTTPException(status_code=400, detail="瀵嗙爜闀垮害鑷冲皯闇€瑕?6 浣?(Password too short)")` -> `manual_review` |
| high | frontend/src/views/chat/DrAI.vue | utf-8 | 0 | 12 | manual_restore_or_regenerate_from_source | L232: `{{ item.pinned ? '取消置顶' : '置顶' }}` -> `manual_review`<br>L240: `{{ item.archived ? '恢复' : '归档' }}` -> `manual_review`<br>L261: `{{ showArchived ? '暂无已归档会话。' : '暂无历史会话，发送第一条消息后会自动生成会话记录。' }}` -> `manual_review` |
| high | docs/blackboard/state.yaml | utf-8 | 1 | 9 | manual_restore_or_regenerate_from_source | L523: `explicit `鐎垫澘鎳撹棢闁稿繐宕?semantics instead of encouraging estimated values, and the page-level status...` -> `manual_review`<br>L530: `- Real PDF validation against `C:\Users\JoeWang\Desktop\闁哄倹婢樼紓鎾诲棘閸ワ附顐藉鍓侇剼濞达絾鎸婚ˉ鍛偘?pdf` confirme...` -> `manual_review`<br>L540: `and a frontend dev server on `127.0.0.1:4173` confirmed the live OCR success branch with the real...` -> `manual_review` |
| high | frontend/src/views/ClinicalView.vue | utf-8 | 0 | 8 | manual_restore_or_regenerate_from_source | L34: `<span class="text-2xl">{{ anomalySummary.status === 'alert' ? '警' : '查' }}</span>` -> `manual_review`<br>L70: `已识别 {{ analysisContextDisplay.counts?.recognized ?? 0 }} 项，已推导 {{ analysisContextDisplay.counts?....` -> `manual_review`<br>L266: `{{ saving ? '保存中...' : '保存健康档案' }}` -> `manual_review` |
| high | tmp_doc_extract/official_spec.txt | not_utf8:UnicodeDecodeError,gb18030_readable | 0 | 1 | manual_restore_or_regenerate_from_source | L198: `示例：[12]Crackton, P. (1987). The Loonie: God's long-awaited gift to colourful pocket change? Canad...` -> `manual_review` |
| medium | backend/rag/build_kb.py | utf-8 | 0 | 2 | inspect_before_batch_fix | L38: `re.compile(r"^\s*第?[一二三四五六七八九十百千\d]+[章节部分篇卷]\s*[、.．\-]?\s*(?P<title>.+?)\s*$"),` -> `manual_review`<br>L39: `re.compile(r"^\s*(?:[（(]?[一二三四五六七八九十百\d]+[）)]?\|\d+(?:\.\d+){0,3})\s*[、.．\-:：]?\s*(?P<title>.+?)\s...` -> `manual_review` |
| medium | backend/rag/pdf_extraction.py | utf-8 | 0 | 2 | inspect_before_batch_fix | L45: `r"^\s*第\s*[一二三四五六七八九十百千0-9]+(?:\.[一二三四五六七八九十百千0-9]+)*\s*[章节编部篇卷部分节]\s*[：:、.\-]?\s*(?P<title>.+?)\...` -> `manual_review`<br>L47: `re.compile(r"^\s*[（(]?[一二三四五六七八九十百千]+[)）]?[、.．:：-]\s*(?P<title>.+?)\s*$"),` -> `manual_review` |
| medium | frontend/src/layout/MainLayout.vue | utf-8 | 0 | 2 | inspect_before_batch_fix | L18: `<el-tag :type="store.deviceStatus === '设备在线' ? 'success' : 'danger'" effect="dark" round>` -> `manual_review`<br>L42: `{{ authStore.user?.username \|\| '加载中...' }}` -> `manual_review` |
| medium | frontend/src/stores/nutritionStore.js | utf-8 | 0 | 2 | inspect_before_batch_fix | L26: `showToast(forceRefresh ? '已重新生成食谱' : '智能食谱生成成功', 'success')` -> `manual_review`<br>L34: `showToast(e.response?.data?.detail \|\| "服务请求失败", 'error')` -> `manual_review` |
| medium | frontend/src/views/admin/DataCenterView.vue | utf-8 | 0 | 2 | inspect_before_batch_fix | L247: `showToast(`${file.name} 上传失败: ${e.response?.data?.detail \|\| e.message}`, 'error')` -> `manual_review`<br>L274: `showToast(e.response?.data?.detail \|\| '启动训练失败', 'error')` -> `manual_review` |
| medium | frontend/src/views/admin/KnowledgeBase.vue | utf-8 | 0 | 2 | inspect_before_batch_fix | L117: `showToast('获取文件列表失败: ' + (e.response?.data?.detail \|\| e.message), 'error')` -> `manual_review`<br>L147: `showToast('上传失败: ' + (e.response?.data?.detail \|\| e.message), 'error')` -> `manual_review` |
| medium | frontend/src/views/clinical/HealthTimeline.vue | utf-8 | 0 | 2 | inspect_before_batch_fix | L100: `{{ simulating ? '推演计算中...' : '开始魔法推演 (Simulate)' }}` -> `manual_review`<br>L401: `symbolSize: hasEnoughData ? 8 : 12, // 数据少时放大数据点` -> `manual_review` |
| medium | backend/debug_db.py | utf-8 | 0 | 1 | inspect_before_batch_fix | L119: `🔧 为什么会这样?` -> `manual_review` |
| medium | backend/rag/benchmark.py | utf-8 | 0 | 1 | inspect_before_batch_fix | L33: `re.compile(r"^\s*(?:[一二三四五六七八九十百千0-9]+(?:[、.．])?)\s*(?P<title>.+?)\s*$"),` -> `manual_review` |
| medium | backend/services/chat_service.py | utf-8 | 1 | 0 | inspect_before_batch_fix | L899: `"recent_metric_anomaly_lookup": "鎸囨爣寮傚父鏁寸悊瀹屾垚",` -> `"recent_metric_anomaly_lookup": "指标异常整理完成",` |
| medium | frontend/src/stores/authStore.js | utf-8 | 0 | 1 | inspect_before_batch_fix | L61: `const errorMsg = error.response?.data?.detail \|\| "注册服务连接失败"` -> `manual_review` |
| medium | frontend/src/views/LifestyleView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L355: `const errorDetail = e.response?.data?.detail \|\| e.response?.data?.message \|\| e.message \|\| '网络异常'` -> `manual_review` |
| medium | frontend/src/views/LoginView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L32: `还没有账号?` -> `manual_review` |
| medium | frontend/src/views/PharmacyView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L34: `<span class="font-bold">{{ analyzing ? '分析中...' : '安全分析 (Analyze)' }}</span>` -> `manual_review` |
| medium | frontend/src/views/RegisterView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L45: `已有账号?` -> `manual_review` |
| medium | frontend/src/views/SettingsView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L63: `{{ changingPassword ? '保存中...' : '💾 保存密码' }}` -> `manual_review` |
| medium | frontend/src/views/admin/UserManagementView.vue | utf-8 | 0 | 1 | inspect_before_batch_fix | L72: `showToast(e.response?.data?.detail \|\| "无法获取用户列表", "error", "bottom-right")` -> `manual_review` |
| medium | tests/test_chat_agent_service.py | utf-8 | 1 | 0 | inspect_before_batch_fix | L806: `assert "cannot" in response["reply"].lower() or "涓嶈兘" in response["reply"]` -> `assert "cannot" in response["reply"].lower() or "不能" in response["reply"]` |
