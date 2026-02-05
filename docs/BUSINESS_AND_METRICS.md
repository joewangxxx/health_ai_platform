# 💰 商业模型与数据指标体系 (Business & Data Metrics)

| 项目 | Health AI Platform | 版本 | V2.0 |
| :--- | :--- | :--- | :--- |
| **文档类型** | 产品商业化指南 | **日期** | 2026-02-05 |

---

## 1. 商业模式设计 (Business Model)

### 1.1 核心商业模式：Freemium (免费+增值)

我们通过免费的基础功能吸引用户，通过高价值的"深度分析"和"家庭管理"功能实现变现。

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户价值金字塔                               │
├─────────────────────────────────────────────────────────────────┤
│                        ┌─────────┐                              │
│                        │ 家庭版  │  ← 高客单价                   │
│                        │  ¥399/年 │    子女为父母付费             │
│                    ┌───┴─────────┴───┐                          │
│                    │    Pro 专业版    │  ← 核心营收               │
│                    │    ¥99/年        │    个人深度用户            │
│                ┌───┴─────────────────┴───┐                      │
│                │       Free 免费版        │  ← 用户获取             │
│                │       基础功能体验        │    转化漏斗顶部          │
│                └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 会员权益矩阵 (Feature Gating)

| 功能模块 | Free (免费版) | Pro (专业版 ¥99/年) | Family (家庭版 ¥399/年) | 价值锚点 |
| :--- | :--- | :--- | :--- | :--- |
| **智能 OCR** | 3页/次，限3次/月 | **无限页数，无限次** | ✅ + 家人共享 | 解决"多页报告"痛点 |
| **Dr. AI 问答** | 基础问答 (无记忆) | **RAG 深度问答 + 上下文** | ✅ + 多人档案切换 | 解决"专业解读"痛点 |
| **健康时光机** | 仅查看历史曲线 | **未来 5-10 年风险推演** | ✅ | 解决"健康焦虑"痛点 |
| **亲情账户** | ❌ 不可关联 | 关联 2 位家人 | **关联 5 位家人** | 解决"异地养老"痛点 |
| **数据导出** | 网页预览 | **专业 PDF 报告** | ✅ + 家庭健康报告 | 解决"就医资料"痛点 |
| **基因分析** | 展示原始 SNP | **药物代谢分析 + 风险归因** | ✅ | 解决"基因解读"痛点 |
| **营养建议** | 通用膳食指南 | **个性化食谱生成** | ✅ | 解决"怎么吃"痛点 |

### 1.3 定价策略依据

| 版本 | 年费 | 月均成本 | 心理锚点 |
|------|------|---------|---------|
| Pro | ¥99/年 | ¥8.25 | < 一杯奶茶 |
| Family | ¥399/年 | ¥33.25 | < 一次体检挂号费 |

---

## 2. 数据指标体系 (Data Metrics)

### 2.1 北极星指标 (North Star Metric)

> **"有效健康闭环数" (Completed Health Loops)**

**定义**：用户在一个 Session 内完成 `上传/录入 → 分析 → 获得建议` 的完整流程。

**计算公式**：
```
Health Loop = (ocr_data_save OR profile_manual_save) 
              AND (ai_chat_query OR timeline_simulate OR recipe_generate)
```

**目标基线**：
| 阶段 | 目标值 | 说明 |
|------|--------|------|
| MVP | 50 loops/day | 验证产品价值 |
| Growth | 500 loops/day | 规模化增长 |
| Scale | 5000 loops/day | 商业化成熟 |

### 2.2 指标金字塔 (Metrics Hierarchy)

```
                    ┌─────────────────────┐
                    │   💰 营收指标        │
                    │   MRR, ARPU, LTV    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
      ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼───────┐
      │  🎯 转化指标   │ │ 📊 活跃指标  │ │  🔄 留存指标   │
      │ Trial→Paid   │ │ DAU/WAU    │ │  D1/D7/D30   │
      └───────┬───────┘ └──────┬──────┘ └───────┬───────┘
              │                │                │
      ┌───────▼────────────────▼────────────────▼───────┐
      │                  🔬 行为指标                      │
      │         OCR 使用率、AI 问答量、功能渗透率           │
      └────────────────────────────────────────────────┘
```

### 2.3 关键埋点设计 (Event Tracking Plan)

为了支持数据分析，需要在前端 (`frontend/src/utils/analytics.js`) 埋入以下事件：

#### A. 核心漏斗 (Core Funnel)

| 事件名 | 触发时机 | 关键属性 | 分析目标 |
|--------|---------|---------|---------|
| `ocr_upload_start` | 点击上传按钮 | `file_type`, `file_size` | 漏斗起点 |
| `ocr_upload_success` | OCR API 返回成功 | `page_count`, `api_time_ms` | API 性能 |
| `ocr_parse_success` | LLM 结构化提取成功 | `fields_extracted`, `parse_time_ms` | 解析质量 |
| `ocr_data_save` | 用户保存/自动保存 | `save_method`, `is_auto` | 漏斗终点 |

**漏斗分析**：
```
ocr_upload_start → ocr_upload_success → ocr_parse_success → ocr_data_save
     100%              ?%                    ?%                 ?%
```

#### B. 活跃度指标 (Engagement)

| 事件名 | 触发时机 | 关键属性 |
|--------|---------|---------|
| `ai_chat_query` | 用户向 Dr. AI 提问 | `query_length`, `has_context` |
| `ai_chat_response` | AI 返回回答 | `response_time_ms`, `source_count` |
| `recipe_generate` | 点击生成食谱 | `calorie_target`, `restrictions[]` |
| `timeline_simulate` | 使用时光机滑块 | `years_forward`, `intervention_enabled` |
| `risk_card_click` | 点击风险详情卡片 | `disease_type`, `risk_level` |

#### C. 商业化指标 (Monetization)

| 事件名 | 触发时机 | 关键属性 | 分析目标 |
|--------|---------|---------|---------|
| `paywall_show` | 触发付费墙展示 | `feature_blocked`, `user_tier` | 付费意愿 |
| `paywall_click_upgrade` | 点击升级按钮 | `source_feature` | 转化入口 |
| `payment_success` | 支付成功 | `plan_type`, `amount`, `channel` | 营收归因 |
| `report_export_pdf` | 点击导出 PDF | `page_count`, `is_pro` | Pro 功能使用 |
| `family_invite_sent` | 发出亲情邀请 | `invite_method` | 病毒系数 |
| `family_invite_accepted` | 邀请被接受 | `inviter_tier` | 邀请转化 |

---

## 3. 技术实现建议 (Technical Implementation)

### 3.1 埋点数据结构

```json
{
  "event_name": "ocr_data_save",
  "user_id": "hashed_user_id",
  "session_id": "uuid_v4",
  "timestamp": 1709876543,
  "client_time": "2026-02-05T02:07:27+08:00",
  "properties": {
    "file_type": "pdf",
    "page_count": 5,
    "parsing_time_ms": 3500,
    "fields_extracted": 12,
    "is_pro": false,
    "is_auto_save": true
  },
  "context": {
    "platform": "web",
    "browser": "Chrome 120",
    "screen_size": "1920x1080"
  }
}
```

### 3.2 前端埋点工具类 (建议实现)

```javascript
// frontend/src/utils/analytics.js

class Analytics {
  constructor() {
    this.queue = []
    this.userId = null
  }

  setUserId(userId) {
    // 哈希处理，不存储原始 ID
    this.userId = this.hashUserId(userId)
  }

  track(eventName, properties = {}) {
    const event = {
      event_name: eventName,
      user_id: this.userId,
      session_id: this.getSessionId(),
      timestamp: Date.now(),
      properties: this.sanitize(properties)
    }
    this.queue.push(event)
    this.flush()
  }

  // 隐私合规：移除敏感数据
  sanitize(props) {
    const sensitiveKeys = ['blood_glucose', 'hba1c', 'cholesterol', 'creatinine']
    const sanitized = { ...props }
    sensitiveKeys.forEach(key => delete sanitized[key])
    return sanitized
  }
}

export const analytics = new Analytics()
```

### 3.3 隐私合规要求 (Privacy Compliance)

| 要求 | 实现方式 |
|------|---------|
| **用户 ID 匿名化** | 使用 SHA256 哈希处理用户 ID |
| **敏感数据禁传** | 严禁上传具体体检数值（如血糖值 5.6） |
| **行为数据脱敏** | 仅统计行为类型（如"上传了血糖数据"） |
| **用户授权** | 首次使用时获取数据收集授权 |
| **数据留存** | 埋点数据保留不超过 90 天 |

### 3.4 数据流向架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   前端      │ →  │   埋点 API   │ →  │   Kafka     │ →  │   ClickHouse│
│  analytics  │    │  /track     │    │   队列      │    │   数据仓库   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ↓
                                                         ┌─────────────┐
                                                         │   Metabase  │
                                                         │   数据看板   │
                                                         └─────────────┘
```

---

## 4. 关键业务看板 (Dashboard Design)

### 4.1 日报核心指标

| 指标名称 | 计算方式 | 健康阈值 |
|---------|---------|---------|
| DAU | 日活跃用户数 | > 100 (MVP) |
| Health Loop Rate | 完成闭环数 / DAU | > 30% |
| OCR 成功率 | ocr_parse_success / ocr_upload_start | > 85% |
| AI 问答量 | ai_chat_query 事件数 | > DAU * 2 |
| 付费转化率 | payment_success / paywall_show | > 3% |

### 4.2 周报趋势分析

- WAU / DAU 比值 (粘性指标)
- 新用户 D7 留存率
- Pro 功能渗透率 (使用 Pro 功能的 Free 用户占比)
- 家庭账户病毒系数 K = 邀请发送数 * 接受率

---

## 5. 阶段性目标 (OKR)

### Phase 1: MVP 验证 (0-3 月)

| Objective | Key Results |
|-----------|-------------|
| 验证核心价值 | OCR 成功率 > 80% |
| | Health Loop Rate > 20% |
| | NPS > 30 |

### Phase 2: 增长期 (3-6 月)

| Objective | Key Results |
|-----------|-------------|
| 规模化获客 | DAU > 1000 |
| | 付费用户 > 100 |
| | 家庭账户激活 > 50 |

### Phase 3: 商业化 (6-12 月)

| Objective | Key Results |
|-----------|-------------|
| 实现盈利 | MRR > ¥10,000 |
| | Pro 续费率 > 60% |
| | LTV/CAC > 3 |

---

*本文档用于指导产品商业化方向和数据埋点开发，由产品团队维护。*
