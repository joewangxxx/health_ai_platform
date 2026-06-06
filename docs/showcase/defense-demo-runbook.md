# HealthAI Platform 答辩演示 Runbook

更新时间：2026-05-07

## 1. 演示目标

本演示围绕同一名演示患者展示多模态健康数据如何进入平台，并最终形成可解释的综合风险结论。

核心叙事：

> 我先上传临床体检数据，建立基础健康画像；再上传基因数据，补充长期易感性；然后通过行为视觉模块回放这名患者一天的睡眠、饮食、久坐和活动；最后执行融合计算，在仪表盘得到多模态证据支持的健康风险解释。

推荐主流程患者：`synthea_8505e011`，展示“代谢与糖尿病高风险”故事。

## 2. 演示前检查

本地服务：

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000/health
- 登录账号：`admin / admin`

推荐浏览器路径：

1. `/login`
2. `/clinical`
3. `/genomics`
4. `/lifestyle`
5. `/`

演示数据清单：

- 患者-文件绑定清单：`data/demo/demo_patient_file_manifest.json`
- 预期融合结果：`data/demo/demo_fusion_expected_results.json`
- 基因文件生成说明：`data/demo/demo_gene_files_manifest.json`

## 3. 患者文件绑定

| 演示患者 | 临床 CSV | 基因 TXT | 行为场景 | 用途 |
| --- | --- | --- | --- | --- |
| `synthea_8505e011` | `data/demo/platform_demo_profile_synthea_8505e011.csv` | `data/demo/demo_gene_synthea_8505e011.txt` | `metabolic_day_001` | 主流程，代谢与糖尿病高风险 |
| `synthea_066c0f3d` | `data/demo/platform_demo_profile_synthea_066c0f3d.csv` | `data/demo/demo_gene_synthea_066c0f3d.txt` | `cardio_hf_day_001` | 备用，心血管与心衰监测 |
| `synthea_4a52ea9c` | `data/demo/platform_demo_profile_synthea_4a52ea9c.csv` | `data/demo/demo_gene_synthea_4a52ea9c.txt` | `younger_improvement_day_001` | 对照，年轻患者改善故事 |

不要混用不同患者的数据。答辩主流程建议全程使用 `synthea_8505e011`。

## 4. 主流程脚本

### 4.1 登录

操作：

1. 打开 http://127.0.0.1:5173/login
2. 输入 `admin / admin`
3. 进入平台主界面

讲解词：

> 这里进入的是 HealthAI Platform 的本地演示环境，接下来我会按照真实健康管理流程，从临床、基因、生活方式三个入口逐步补充同一名演示患者的数据。

### 4.2 临床体检页面

操作：

1. 进入“临床体检 Clinical”
2. 点击“导入 CSV 健康数据”
3. 上传 `data/demo/platform_demo_profile_synthea_8505e011.csv`
4. 确认表单中出现年龄、BMI、血压、血糖、糖化血红蛋白、血脂、肾功能等字段

重点字段：

- 年龄：60
- BMI：29.5
- 血压：188 / 116
- 空腹血糖：4.46
- 糖化血红蛋白：5.9
- 总胆固醇：4.39
- 甘油三酯：1.62
- 睡眠基线：6 小时

讲解词：

> 第一步是临床画像。CSV 导入不是直接跑模型，而是先把体检数据结构化，形成系统后续分析可以读取的健康画像。这里可以看到该患者存在明显的血压异常、BMI 偏高，以及代谢相关指标压力。

### 4.3 基因组学页面

操作：

1. 进入“基因组学 Genomics”
2. 上传 `data/demo/demo_gene_synthea_8505e011.txt`
3. 等待解析成功
4. 确认预览表出现 SNP 记录

数据说明：

- 文件格式是 23andMe-style 四列文本：`rsid chromosome position genotype`
- 该文件包含 50,000 个 SNP
- rsID 和风险等位基因来自本地 GWAS 权重库；个人 genotype 是合成演示数据
- 不是一份真实个人基因组，也不是临床级遗传检测报告

讲解词：

> 第二步加入基因组学信息。临床体检反映当前健康状态，而基因数据提供长期易感性背景。这里使用的是合成的演示基因型文件，但位点来自平台本地 GWAS 权重库，因此能够真实参与后续融合计算。

### 4.4 行为视觉页面

操作：

1. 进入“行为视觉 Lifestyle”
2. 在演示患者选择框中选择 `代谢与糖尿病高风险演示日 (synthea_8505e011)`
3. 点击“加载演示患者”
4. 点击播放或重播一天时间线
5. 依次展示睡眠、高碳水早餐、晨间生命体征、久坐、高钠午餐、低强度步行、晚间久坐、高碳水晚餐、全天汇总

重点行为证据：

- 步数：4100 步
- 活动：18 分钟
- 久坐：610 分钟
- 睡眠：5.7 小时
- 热量：2200 千卡
- 钠：5050 毫克
- 饮食模式：高钠高碳水

讲解词：

> 第三步是生活方式上下文。这里不是从真实设备同步，而是模拟演示患者的一天行为时间线。它帮助解释为什么单纯的临床风险会进一步被生活方式放大，例如睡眠不足、久坐、高碳水和高钠饮食都与代谢风险叙事一致。

必须说明的边界：

> 这里的行为时间线是 `simulated_demo`，不是实际穿戴设备、真实摄像头或 IoT 数据。演示回放不会自动保存图像、物联网数据或健康历史。

### 4.5 融合计算与仪表盘

操作：

1. 在行为视觉页点击“使用该演示场景生成风险解释”或融合计算按钮
2. 等待跳转到仪表盘
3. 展示综合风险报告

主患者预期结果摘要来自 `data/demo/demo_fusion_expected_results.json`：

| 风险项 | 预期风险 | 讲解重点 |
| --- | --- | --- |
| Hypertension | 99.9 | 临床血压极高，基因和生活方式进一步放大 |
| HighLipid | 99.9 | 血脂相关模型高风险，受基因与生活方式共同影响 |
| CKD | 99.9 | 高血压、代谢压力和融合系数使肾脏风险升高 |
| CoronaryHeart | 97.7 | 心血管风险受血压、血脂、遗传背景和行为因素共同驱动 |
| InsulinResist | 78.6 | BMI、糖化血红蛋白和代谢相关基因背景支持解释 |

讲解词：

> 这里的结果不是某一个单点模型的输出，而是临床风险、基因修正因子和生活方式修正因子共同作用后的综合解释。仪表盘最重要的价值不是只告诉用户分数高，而是能追溯到数据来源：体检、基因和一天行为模式分别贡献了什么。

## 5. 其他模块展示顺序

主流程完成后，用其他模块展示平台不是只做风险评分，而是覆盖“解释、干预、管理”的闭环。

### Dr. AI 健康顾问

推荐提问：

1. `请根据我刚才的体检、基因和生活方式数据，解释为什么我的代谢风险较高。`
2. `如果我想优先降低糖尿病和高血压风险，前三个干预动作是什么？`
3. `这些建议有哪些证据来源？哪些只是一般健康建议？`

讲解重点：

- 多轮问答
- 证据标签
- RAG/知识库辅助
- 不替代医生诊断

### AI 营养师

推荐提问：

1. `请为这名高钠高碳水饮食患者生成一周饮食调整建议。`
2. `如果早餐习惯是粥、馒头、甜豆浆，如何替换得更适合控糖？`

讲解重点：

- 从风险解释转向干预建议
- 生活方式闭环
- 个性化但非医疗处方

### 智能药房

推荐场景：

- 使用 `synthea_066c0f3d`
- 讲心血管/心衰患者的用药安全、潜在相互作用和基因背景

讲解重点：

- 药物安全辅助
- 临床 + 基因 + 生活方式上下文
- 当前为演示建议，不替代处方

### 全周期慢病管理

推荐讲法：

> 风险评估只是入口，慢病管理模块体现的是后续长期随访、趋势记录和干预闭环。平台从一次体检数据扩展为持续健康管理系统。

## 6. 失败兜底材料

答辩现场建议提前准备：

- 登录后首页截图
- 临床 CSV 导入成功截图
- 基因文件解析成功截图
- 行为时间线截图
- 仪表盘融合结果截图
- 30 到 60 秒完整主流程录屏

已经可复用的证据截图目录：

- `output/playwright/`

推荐新录屏文件名：

- `output/playwright/defense-main-flow-synthea_8505e011.mp4`

## 7. 常见问答

问题：这些患者是真实患者吗？

回答：

> 不是。患者画像来自 Synthea 风格的合成数据，基因型和行为时间线也是演示用途的合成数据。这样可以展示完整流程，同时避免真实患者隐私风险。

问题：基因数据是真实的吗？

回答：

> 文件中的 rsID 和风险等位基因来自平台本地 GWAS 权重库，格式模拟 23andMe 原始数据；但每个患者的 genotype 是合成的，不代表真实个人基因组。

问题：行为视觉数据是真实设备采集的吗？

回答：

> 不是。当前是 `simulated_demo` 行为时间线，用来展示系统如何接收生活方式上下文。它不上传图像原始文件，也不写入真实 IoT 同步。

问题：融合结果可以作为临床诊断吗？

回答：

> 不能。当前结果用于健康风险解释和演示，不是临床诊断。平台强调可解释、可追溯和辅助决策，最终诊断仍需要医生和真实临床验证。

## 8. 最短演示版

如果时间只有 5 分钟：

1. 上传 `synthea_8505e011` 临床 CSV
2. 上传 `synthea_8505e011` 基因 TXT
3. 加载 `metabolic_day_001`
4. 展示一天时间线中的睡眠、饮食和久坐
5. 点击融合计算
6. 在仪表盘解释高血压、血脂、CKD、冠心病和胰岛素抵抗风险
7. 用一句话带过 Dr. AI、营养师、药房和慢病管理模块

## 9. 完整演示版

如果时间有 8 到 10 分钟：

1. 30 秒：登录和平台定位
2. 90 秒：临床 CSV 上传
3. 90 秒：基因 TXT 上传
4. 2 分钟：行为视觉一天时间线
5. 90 秒：融合计算和仪表盘解释
6. 2 分钟：Dr. AI、营养师、药房、慢病管理扩展展示
7. 30 秒：边界说明和总结

结束语：

> 这个项目的重点不是单点 AI 模型，而是把临床、基因、生活方式和智能建议组织成一个可追溯的健康管理闭环。演示数据是合成的，但流程、接口、数据结构和验证链路是完整的。

## 2026-05-13 Lifestyle behavior upload path

Use this path when the defense/demo should show user-provided lifestyle behavior rather than only prepared scenarios.

1. Open `/lifestyle` after Clinical/OCR and optional Genomics setup.
2. Choose a platform-standard behavior-day `.csv` or `.json` file.
3. Optionally provide `patient_id` and `local_date` only when they match the file content.
4. Upload through the Lifestyle page.
5. Point out that the backend route is authenticated multipart `POST /api/v1/lifestyle/import-behavior-day`.
6. On success, show the generated timeline and `lifestyle_context` as `user_uploaded` preview data.
7. Run analysis only as an explicit user action, using the returned `lifestyle_context.v1` as provenance-labeled heuristic context.

Required boundary wording:

> This upload is parse-only and validation-only. It does not persist the file, write IoT/device rows, save profile fields, create health-history records, create medical documents, or save risk snapshots. Uploaded behavior remains `data_mode="user_uploaded"`, and the real-device API is still a placeholder, not a connected device integration.

Error behavior to know before the demo:

- Mismatched `patient_id` or `local_date`: structured `400` validation.
- Malformed behavior data: structured `400` validation.
- File over 1 MB: `413`.
- Unsupported extension or content type: `415`.

Current evidence:

- Focused backend behavior upload regression: `18 passed`.
- Focused frontend Lifestyle behavior/demo node tests: `15 passed`.
- Full backend regression: `269 passed`.
- Frontend production build: passed.
- Live contract probes and headed browser upload artifacts: `output/playwright/behavior-upload-contract-probes.json` and `output/playwright/behavior-upload-live-e2e.json`.
