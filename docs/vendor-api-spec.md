# 神笔小罗 · 管理后台数据接口（商汤开发参考）

> 面向：商汤后端开发  
> 对应需求：《神笔小罗｜管理后台 Dashboard PRD》最新版（见 `docs/PRD_latest.docx`）  
> 风格参考：智多星 `dashboardTrackApi`（POST + JSON、统一响应、`daIds` / `identity` 公共参数、`userRoleInfo` 角色查询）  
> 状态：**草案，待商汤评估**。带 `[TBD]` 的条目需双方确认后定稿。

---

## 0. 设计原则

1. **只提供「原始事实」，不需要预聚合指标。**
   活跃 / 休眠 / 沉默、各种率、环比、预算使用率等**全部由我方看板后端按 PRD 口径计算**。
   这样同一份数据在全景、DA、用户、费用四个 Tab 与导出里数字可互相追溯（PRD 验收 2、3、7）。
   智多星接口里「直接返回 `activeRate` / `silentRate`」的做法**不适用于本项目**：
   PRD 要求任意筛选 + 任意自定义周期都能给出每个率的分子分母，不可能预置所有组合。
2. **粒度：账号 × 自然日。** 沉默判定要回看「连续 60 天」，活跃天数要「去重自然日」，趋势要按周/月切，只有日粒度事实才能支撑。
3. **历史完整。** 数据须覆盖平台上线日 **2026-07-01** 至今，任何接口都可查询整个区间（沉默判定需要回看周期开始前 60 天）。
4. **权限由商汤侧身份体系给出，我方后端按 DA 范围裁剪。** 见 §7。

### 0.1 与智多星 `dashboardTrackApi` 的主要差异

| 项 | 智多星 | 神笔小罗|
|---|---|---|
| 账号类型 | `loginType`：0 PLUS / 1 共享 | `accountType`：`PLUS` / `SUPER`（**没有共享账号**，1 手机号 = 1 账号 = 1 用户） |
| 用户身份 | `customer` / `staff` / `other` | PRD 只有 客户 / 员工：`customer` / `staff`。**`other` 请明确归属**（见 §2.1 备注） |
| 比率 | 接口直接返回百分数 | **不返回比率**，返回可累加的原始计数 |
| 时间粒度 | 月 / 区间汇总 | 账号 × 自然日 |
| 新增 | — | 来源标签（采购/免费）、配置额度、日花费（元）、开通/首次登录时间、账号类型变更记录 |

---

## 1. 公共约定

### 1.1 基础信息

```
基础路径：http://{host}:{port}/api/shenbiDashboardApi/
Content-Type：application/json
统一响应：{ "code": 200, "success": true, "msg": "...", "data": T }
```

> 路径前缀 `shenbiDashboardApi` 为建议命名，可按习惯调整；**字段名与结构请保持一致**。

### 1.2 鉴权与身份

- 服务间鉴权：`[TBD]` API Key / Bearer Token / 内网白名单，请商汤定。
- 登录用户身份：沿用智多星约定，Gateway 注入请求头 `loggedInUserId`，原样透传给接口。

### 1.3 公共筛选参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `daIds` | `number[]` | 空/不传 = 全部 DA；传入 = 按列表筛选。**须再与调用者可见 DA 取交集**（见 §7） |
| `startDate` / `endDate` | `string` | `yyyy-MM-dd`，**均必传**，闭区间，按北京时间（UTC+8）自然日切分 |
| `accountType` | `string` | `PLUS` / `SUPER`；空 = 全部 |
| `identity` | `string` | `customer` / `staff`；空 = 不过滤 |

### 1.4 分页（数据量大的接口）

请求：`page`（从 1 开始，默认 1）、`pageSize`（默认 1000，最大 **5000**）；  
响应：`total` / `page` / `pageSize` / `records`。

### 1.5 时间与数值

- 日期 `yyyy-MM-dd`；时间 `yyyy-MM-dd HH:mm:ss`；时区统一 **UTC+8**。
- 金额单位：**元**，保留 2 位小数；次数为整数。
- 布尔用 `true/false`，缺失值用 `null`，**不要用空字符串或 0 代替缺失**。

---

## 2. 接口总览

| # | 路径 | 方法 | 说明 | 优先级 |
|---|---|---|---|---|
| 1 | `/dataStatus` | GET | 数据截至时间、数据起始日、更新频率 | P0 |
| 2 | `/daList` | GET | DA 字典 | P0 |
| 3 | `/accountList` | POST | 账号主数据（含属性、状态、开通/首次登录时间） | P0 |
| 4 | `/accountTypeHistory` | POST | 账号类型（PLUS/SUPER）变更记录 | P1 |
| 5 | `/quotaConfig` | POST | 配置额度（可开通账号个数） | P0 |
| 6 | `/usageDaily` | POST | 账号 × 日 × 事件类型 的使用次数 | **P0（核心）** |
| 7 | `/costDaily` | POST | 账号 × 日 的 token 与花费（元） | P0 |
| 8 | `/userRoleInfo` | GET | 登录用户角色与可见 DA | P0 |

---

## 3. 基础信息

### 3.1 数据状态 `GET /dataStatus`

用于页面「数据截至时间」和统计截止日的计算（PRD 三·0：当月未结束时统计截止日 = 数据截至时间所在日）。

响应 `data`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `asOf` | string | 数据截至时间 `yyyy-MM-dd HH:mm:ss`。**该时刻之前的数据保证完整** |
| `dataStartDate` | string | 数据起始日，预期 `2026-07-01` |
| `updateFrequency` | string | 例如 `T+1`。`[TBD]` PRD 待商汤确认 |
| `fxVersion` | string | token↔人民币换算比例版本号，例如 `v2026.07`。`[TBD]` |

```json
{ "code": 200, "data": { "asOf": "2026-09-14 06:00:00", "dataStartDate": "2026-07-01", "updateFrequency": "T+1", "fxVersion": "v2026.07" } }
```

### 3.2 DA 字典 `GET /daList`

| 字段 | 类型 | 说明 |
|---|---|---|
| `daId` | number | DA ID |
| `daCode` | string | **DA 代码**：`BC LC GI HEMA OPH NS&RD INF IMMU NMA HSA MCE`（见 PRD 2.1） |
| `daName` | string | 例如 `乳腺癌 BC` |
| `groupName` | string | `肿瘤` / `非肿瘤` / `Access` |
| `isTest` | boolean | 是否测试 DA（测试 DA 的账号不进入统计） |

```json
{ "code": 200, "data": [
  { "daId": 1, "daCode": "BC", "daName": "乳腺癌 BC", "groupName": "肿瘤", "isTest": false },
  { "daId": 9, "daCode": "NMA", "daName": "全国准入 NMA", "groupName": "Access", "isTest": false }
] }
```

> 无法映射到上述 DA 的账号请返回 `daId = null`，页面显示「待映射」，且视为「非 DA 账号」。

---

## 4. 账号数据

### 4.1 账号主数据 `POST /accountList`

**每个账号一行**。支持全量与增量（`updatedSince`）。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `daIds` / `accountType` / `identity` | — | 否 | 同 §1.3 |
| `updatedSince` | string | 否 | `yyyy-MM-dd HH:mm:ss`，只返回此后有变更的账号 |
| `page` / `pageSize` | number | 否 | 同 §1.4 |

响应 `data.records[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `accountId` | number | 账号 ID（**主键**；事件、花费接口均用它关联） |
| `username` | string | 登录账号 |
| `name` | string | 姓名 |
| `phone` | string | 联系电话（完整号码；请返回原值） |
| `daId` | number \| null | 所属 DA；无法映射为 null |
| `region` | string \| null | **大区**：导入账号时管理员填写的大区标签 |
| `colleagueName` | string \| null | 负责同事 / 圈长（DA 三率看板可按「圈长」维度） |
| `identity` | string | `customer` / `staff` |
| `accountType` | string \| null | `PLUS` / `SUPER`；缺失为 null（显示「待映射」，月度预算不计） |
| `sourceTag` | string \| null | **账号来源标签**：`采购` / `免费` |
| `accountStatus` | string | `enabled` / `disabled` |
| `disabledAt` | string \| null | 停用时间。**必须提供**：「有效账号」按统计截止日是否已停用判定，月中停用的账号整月计预算 |
| `openedAt` | string | **开通（导入生效）时间**：PRD「累计开通账号」「开通满 60 天才判沉默」依赖它 |
| `firstLoginAt` | string \| null | **首次登录时间**（PRD「激活账号 = 开通后曾登录过」）；从未登录为 null |
| `isTestAccount` | boolean | **测试账号标识**（按系统账号身份标签，PRD 不另维护名单） |
| `isDaAccount` | boolean | **是否 DA 账号**（false = 非 DA 账号，「核心业务」口径剔除） |
| `remark` | string \| null | 备注 |
| `updatedAt` | string | 最近变更时间 |

```json
{ "code": 200, "data": { "total": 262, "page": 1, "pageSize": 1000, "records": [
  { "accountId": 2468, "username": "zhangsan", "name": "张三", "phone": "13800000000",
    "daId": 1, "region": "东区", "colleagueName": "李四", "identity": "staff",
    "accountType": "PLUS", "sourceTag": "采购",
    "accountStatus": "enabled", "disabledAt": null,
    "openedAt": "2026-07-03 10:20:00", "firstLoginAt": "2026-07-03 11:02:41",
    "isTestAccount": false, "isDaAccount": true, "remark": null, "updatedAt": "2026-09-01 08:00:00" }
] } }
```

> **备注**：智多星的 `identity=other` 在神笔里请明确：是归为 `staff`、`customer`，还是用 `isTestAccount=true` 标出。PRD 用户身份只有「客户 / 员工」。  
> `[TBD]` 目前 PLUS/SUPER 在账号体系里写在「备注」中（崔建良批注）；**请在账号属性里给出结构化的 `accountType`**，否则看板无法可靠区分。

### 4.2 账号类型变更记录 `POST /accountTypeHistory`（P1）

PRD 5：「月中改档的账号按**月末账号类型**取月度预算」。若不提供，只能取当前类型。

请求体：`daIds`（可选）、`startDate`、`endDate`（变更发生日范围）。

响应 `data[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `accountId` | number | |
| `accountType` | string | 变更后的类型 `PLUS` / `SUPER` |
| `effectiveFrom` | string | 生效日期 `yyyy-MM-dd` |

---

## 5. 配置额度

### 5.1 `POST /quotaConfig`

PRD 三·2：**配置额度 = 已配置可开通的账号个数（N1 + M1），单位是「个」，不是金额**。  
额度是**动态可变**的（活动激励会增加），请返回带生效日期的历史。

请求体：`daIds`（可选）。

响应 `data[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `daId` | number | |
| `accountType` | string | `PLUS`（N1）/ `SUPER`（M1） |
| `quota` | number | 额度（个） |
| `effectiveFrom` | string | 生效日期 `yyyy-MM-dd`；统计时取「生效日 ≤ 统计截止日」的最新一条 |
| `note` | string \| null | 变更原因，如「活动激励」 |

```json
{ "code": 200, "data": [
  { "daId": 1, "accountType": "PLUS",  "quota": 22, "effectiveFrom": "2026-07-01", "note": null },
  { "daId": 1, "accountType": "SUPER", "quota": 3,  "effectiveFrom": "2026-07-01", "note": null },
  { "daId": 1, "accountType": "PLUS",  "quota": 25, "effectiveFrom": "2026-08-21", "note": "活动激励" }
] }
```

> **依赖说明（PRD 批注）**：额度「限制」需要在**智多星开通侧**实现（神笔只有读取权限），Grace Shi 已回复「纳入需求」。  
> 看板只**读取**额度用于导入率；若无额度数据，导入率整项显示「待接入」。

---

## 6. 使用事件与花费（核心）

### 6.1 事件口径（请商汤接口按此统计）

| 概念 | 定义（PRD 三·0） |
|---|---|
| **有效功能操作** | 用户主动发起、且请求实际进入神笔服务处理链路的核心功能行为：PubMed 检索、大纲生成、PPT 生成、推文生成、海报生成、内容库分享。**无论最终成功、失败或取消均计入** |
| **成功生成** | PPT / 推文 / 海报生成任务成功完成；失败与取消**不计** |
| **内容导出** | 用户在神笔里**成功下载或导出**已生成的 PPT / 推文 / 海报文件（与后台「数据导出」无关） |
| **使用** | 看板由此判定「活跃」：PubMed 检索 / 大纲生成 / 内容库分享，或**成功**生成 PPT/推文。**只登录、失败或取消的生成、纯导出，都不算使用**，所以 `login` 必须单独提供 |

### 6.2 `POST /usageDaily`

账号 × 自然日 × 事件类型 汇总。**没有事件的日子不需要返回行。**

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `daIds` / `accountType` / `identity` | — | 否 | 同 §1.3 |
| `startDate` / `endDate` | string | **是** | |
| `accountIds` | `number[]` | 否 | 指定账号（账号详情抽屉按需查询） |
| `page` / `pageSize` | number | 否 | 同 §1.4 |

响应 `data.records[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `accountId` | number | |
| `date` | string | `yyyy-MM-dd` |
| `eventType` | string | 见下表 |
| `subType` | string \| null | 子功能，仅生成类需要，见下表 |
| `count` | number | 当日该事件**发起次数**（成功 + 失败 + 取消） |
| `successCount` | number \| null | 其中**成功**次数；仅生成类必填，其余类型传 null |

`eventType` 取值：

| eventType | 含义 | 需 `successCount` | 备注 |
|---|---|---|---|
| `login` | 成功登录神笔 | 否 | 看板用于「激活」「登录未使用」。同日多次可汇总为次数 |
| `pubmed_search` | PubMed 检索 | 否 | |
| `outline_generate` | 大纲生成 | 否 | |
| `library_share` | 内容库分享 | 否 | |
| `ppt_generate` | PPT 生成 | **是** | 有 `subType` |
| `tweet_generate` | 推文生成 | **是** | 有 `subType` |
| `poster_generate` | 海报生成 | **是** | 海报上线前不返回 |
| `ppt_export` | PPT 成功导出 | 否 | `count` 即成功导出次数 |
| `tweet_export` | 推文成功导出 | 否 | |
| `poster_export` | 海报成功导出 | 否 | 海报上线前不返回 |

`subType` 取值（PRD 1.5）：

| 主类型 | subType | 中文 |
|---|---|---|
| `ppt_generate` | `literature_interpretation` | 文献解读 |
| `ppt_generate` | `academic_creation_pro` | 学术创作Pro |
| `tweet_generate` | `medical_popular_science` | 医学科普 |
| `tweet_generate` | `professional_academic` | 专业学术 |
| `tweet_generate` | `guideline_policy` | 指南/政策解读 |

```json
{ "code": 200, "data": { "total": 18432, "page": 1, "pageSize": 5000, "records": [
  { "accountId": 2468, "date": "2026-09-03", "eventType": "login",            "subType": null, "count": 2, "successCount": null },
  { "accountId": 2468, "date": "2026-09-03", "eventType": "pubmed_search",    "subType": null, "count": 3, "successCount": null },
  { "accountId": 2468, "date": "2026-09-03", "eventType": "ppt_generate",     "subType": "literature_interpretation", "count": 2, "successCount": 1 },
  { "accountId": 2468, "date": "2026-09-03", "eventType": "ppt_export",       "subType": null, "count": 1, "successCount": null }
] } }
```

**为什么要这样的粒度（对应 PRD 指标）：**

| PRD 指标 | 依赖字段 |
|---|---|
| 活跃 / 休眠 / 沉默、活跃天数、连续未使用天数、最近使用日期 | `date` + 「使用」类事件（含 `successCount`） |
| 登录未使用账号、本期登录 | `login` |
| 功能使用次数（有效功能操作） | `count`（成败均计） |
| 成功生成次数、人均生成次数、生成转化率 | `successCount` |
| 导出率 | `*_export.count` ÷ `*_generate.successCount` |
| 功能使用分布 / Top N | `subType` |
| 按周/月趋势、账号详情抽屉按周趋势 | `date` |

### 6.3 日花费 `POST /costDaily`

PRD 三·5：花费金额 = 账号使用神笔产生的 **token 消耗**，按 token↔人民币换算比例折算，单位元，保留 2 位小数。

请求体：同 §6.2（`startDate` / `endDate` 必传）。

响应 `data.records[]`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `accountId` | number | |
| `date` | string | |
| `feature` | string | `ppt` / `tweet` / `poster` / `other`。`[TBD]` 依赖商汤**按次回传 token**；若暂时做不到，统一返回 `other`，看板「按功能拆分」会标注为估算 |
| `tokenCount` | number | 当日该功能 token 消耗 |
| `amountCny` | number | 折算后的金额（元，2 位小数）。**请以商汤接口换算为准，我们这边不二次换算** |
| `fxVersion` | string | 所用换算比例版本，需与 §3.1 一致或可追溯。`[TBD]` |

```json
{ "code": 200, "data": { "total": 3120, "page": 1, "pageSize": 5000, "records": [
  { "accountId": 2468, "date": "2026-09-03", "feature": "ppt",   "tokenCount": 1520000, "amountCny": 28.31, "fxVersion": "v2026.07" },
  { "accountId": 2468, "date": "2026-09-03", "feature": "tweet", "tokenCount": 310000,  "amountCny": 7.92,  "fxVersion": "v2026.07" }
] } }
```

**对账要求**：同一账号同一天，所有 `feature` 的 `amountCny` 之和即当日花费；看板验收 7 要求「本月花费 = DA 排行各行之和 = 个人明细各行之和 = 导出合计」，请保证金额不在商汤侧二次四舍五入造成明细与汇总不一致（建议明细保留 2 位后求和）。

> `[TBD]`（PRD 批注，需商汤确认）：① 是否确实没有跨月透支；② 当月消耗接近 600 / 1200 元时，是立即停止还是允许进行中的任务跑完。该结论影响「预算使用率」是否可能超过 100%，看板按如实显示处理。

---

## 7. 用户角色与 DA 权限

### 7.1 `GET /userRoleInfo?userId={userId}`

沿用智多星接口（`userId` 来自请求头 `loggedInUserId`）。

响应 `data`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `userId` / `userName` | — | |
| `roleCode` | string | `super-admin` / `da-manager` / `ordinary-user` |
| `daId` / `daName` | — | 所属 DA，可能为 null |
| `managedDaIds` | `number[]` | 可见 DA：super-admin=全部，da-manager=管辖 DA，ordinary-user=所属 DA |

**角色映射（我方使用）：**

| 商汤 `roleCode` | 看板角色 | 可见范围 |
|---|---|---|
| `super-admin` | 超级管理员 | 全平台、全部 DA；可见费用 Tab；可编辑 AI 洞察；可见完整手机号 |
| `da-manager` | DA 管理员 | 仅 `managedDaIds`；可见费用 Tab（仅本 DA）；洞察只读；手机号脱敏 |
| `ordinary-user` | 其他角色 | **不显示「费用看板」Tab** |

### 7.2 数据范围校验（重要）

PRD 5.5 / 验收 5：**DA 管理员无法通过页面参数、导出接口或下载链接读取其他 DA 数据。**  
后端会在查询前与 `managedDaIds` 取交集；**商汤各接口也请对 `daIds` 与调用者可见范围取交集**，不要依赖调用方自觉（双重保险）。

---

## 8. 一致性与验收（建议联调时逐项核对）

| # | 检查项 | 方法 |
|---|---|---|
| 1 | 账号数 | `accountList` 的账号数 = 商汤后台导出的账号总数；`isTestAccount=false` 的数量与 PRD 统计口径一致 |
| 2 | 事件完整性 | 任取 3 个账号 × 一周，`usageDaily` 求和 = 商汤后台操作明细（`operationRecords` 类接口）计数 |
| 3 | 成功/失败 | `ppt_generate.successCount ≤ count`；失败/取消的生成不出现在 `successCount` 中 |
| 4 | 登录 vs 使用 | 只登录没有任何使用记录的账号，只有 `login` 行 |
| 5 | 导出 | `ppt_export.count` = 用户在神笔里成功下载 PPT 的次数（同一内容重复导出重复计算）。`[TBD]` 能否按内容去重 |
| 6 | 花费 | 同一月，`costDaily` 全账号金额之和 = 商汤财务口径的当月 token 费用（按同一换算比例） |
| 7 | 时区 | 23:59:59 与 00:00:00 附近的事件落在正确的自然日（UTC+8） |
| 8 | 历史 | 能查到 2026-07-01 起每一天的数据 |
| 9 | 权限 | 用 da-manager 的 `loggedInUserId` 请求其他 DA 的 `daIds`，返回空集而非越权数据 |

---

## 9. 错误码

| 情况 | 表现 |
|---|---|
| 必填时间参数缺失 / 格式错误 | `code != 200`，`msg` 为中文原因 |
| `startDate > endDate` | `code != 200` |
| `pageSize` 超过上限 | 按上限截断，或 `code != 200`（请明确） |
| 区间内无数据 | `code = 200`，`records = []`（**不是错误**） |
| 无权限的 DA | 与无数据一致：返回空集，不报错 |

---

## 10. 待确认清单（汇总）

| # | 问题 | 影响 |
|---|---|---|
| 1 | 数据更新频率（T+1？几点完成？） | 数据截至时间、环比口径 |
| 2 | token ↔ 人民币换算比例与版本 | 所有费用指标 |
| 3 | 能否**按次**回传 token 并区分功能 | 账号费用详情「按功能拆分」 |
| 4 | 导出能否按内容标记去重 | 导出率口径（PRD 4 中 [TBD]） |
| 5 | PLUS / SUPER 的结构化字段 | 目前仅在备注中；账号类型、预算 |
| 6 | `identity=other` 的归属 | 客户 / 员工二分 |
| 7 | 测试账号 / 非 DA 账号的系统标识 | 「全平台」「核心业务」口径 |
| 8 | 账号类型变更记录能否提供 | 月中改档的月度预算 |
| 9 | 额度（N1 / M1）的存储位置与变更记录；开通侧限制由谁实现 | 导入率；PRD 批注已纳入需求 |
| 10 | 是否存在跨月透支；接近 600 / 1200 元时的处理策略 | 预算使用率语义 |
| 11 | 海报上线时间与事件命名 | 海报相关指标开关 |
| 12 | 服务间鉴权方式 | 联调 |

---

## 附：适配说明

- 我方后端已定义内部数据契约 `backend/app/vendor/dataset.py`（`AccountRec` / `Event` / `CostRec` / `quotas` / `as_of`），
  本文档接口与之一一对应：`accountList → AccountRec`，`usageDaily → Event`，`costDaily → CostRec`，`quotaConfig → quotas`，`dataStatus → as_of`。
- 我方只信任 Gateway 注入的请求头 `loggedInUserId`（注意大小写，需原样透传），不接受前端传入的角色。
