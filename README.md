# 神笔小罗 · 管理后台 Insight 分析

## 项目简介

「神笔小罗」是面向医学部与各 DA(治疗领域)团队的 AI 内容生成工具,可以生成 PPT(文献解读、学术创作 Pro)和推文(医学科普、专业学术、指南政策解读),并支持 PubMed 检索、大纲生成和内容库分享。

本项目是它的**管理后台数据看板**。运营和 DA 管理员用它回答三类问题:
- 账号有没有被用起来:开通、激活、活跃、休眠、沉默的账号各有多少,哪些「登录了但没使用」,值得优先唤醒。
- 用得怎么样:各功能的使用与成功生成次数、导出率、使用深度分层、按周/月趋势。
- 花了多少钱:token 费用、预算使用率、按功能和按账号的费用拆分。

### 四个看板
| Tab | 内容 |
|---|---|
| 全景看板 | 全平台/核心业务的开通、激活、活跃、沉默、导入率,功能使用分布,环比与趋势,AI 洞察 |
| DA 数据下钻 | 按 DA 对比三率(导入/激活/活跃),单个 DA 的账号与功能明细 |
| 用户数据下钻 | 账号清单、休眠/沉默名单(含「本期登录」标签)、单账号按周趋势 |
| 费用看板 | 费用趋势、功能费用分布、账号费用明细、预算使用率(仅超级管理员与 DA 管理员可见) |

### 主要特点
- **指标全部由后端按 PRD 口径计算**,前端只负责展示;同一份数据在四个 Tab、导出报告里可以互相对账。
- **只依赖「账号 × 自然日」的原始事实**(登录、各类使用事件、费用、额度),不依赖预聚合指标,所以任意筛选和自定义周期都能给出分子分母。
- **按角色裁剪数据范围**:超级管理员看全平台,DA 管理员只看所辖 DA,其他角色看不到费用 Tab,手机号按角色脱敏。
- **可导出单文件 HTML 报告**(16:9 分页,可打印为 PDF)和各表格明细。
- **数据源可切换**:开发期用本地上传文件加模拟补齐,联调和上线时切到乙方(商汤)接口。

### 技术栈
- 后端:Python、FastAPI、SQLAlchemy(默认 SQLite,可换 PostgreSQL)
- 前端:React 19、Vite、Tailwind 4、shadcn/ui、Recharts
- AI 洞察:可选,配置 `LLM_*` 环境变量后启用,不配置则自动跳过

### 当前状态
- 四个 Tab、角色权限、HTML 报告导出均已可用,后端测试覆盖 PRD 验收项。
- 乙方 3 个接口(`dataStatus`/`usageDaily`/`costDaily`)已按定稿文档适配:`/api/dashboard` 路径、`code=0` 响应、`article_*` 推文事件、CNY/USD 分币种费用。美元汇率由 env 的 `USD_CNY_RATE` 配置(默认 7.20 为占位值,上线前按财务口径修改)。
- 统一门户提供的账号、额度、角色等 5 个接口,文档尚未拿到,字段名与路径仍沿用草案假设(路径前缀可用 `VENDOR_PORTAL_API_PREFIX` 配置),拿到文档后需逐项核对。

> 本仓库只包含代码。用户数据、数据库、`env` 配置和排除名单种子文件(`backend/data/exclusion_seed.json`)都不入库,新环境需要自行准备。

---

按《神笔小罗｜管理后台 Dashboard PRD v1.1》实现:**全景看板 / DA 数据下钻 / 用户数据下钻 / 费用看板** 四个同级 Tab。以下为开发与部署说明。

## 启动
```bash
cd backend && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m scripts.seed_local     # 用 临时后台开发数据包/数据源 初始化 data/insight.db
cd ../frontend && npm install
cd .. && ./dev.sh start                      # 后端 8420,前端 vite(侧边栏「身份(联调)」切换角色)
```
测试:`cd backend && PYTHONPATH=. ./.venv/bin/python -m pytest tests`(覆盖 PRD 验收 2/3/5/7/8/9)。

## 架构
- `backend/app/vendor/dataset.py`:**数据契约**(账号、日粒度使用事件、日花费、配额)。指标引擎只依赖它。
- `vendor/local_adapter.py`:本地三份上传文件 → Dataset;PRD 需要而文件里没有的字段由 `mock_fill.py` 确定性补齐,
  响应里带 `meta.mock_fields`,前端显示「含模拟数据」。`MOCK_FILL=0` 可关闭。商汤接口就绪后新增 vendor adapter 即可替换。
- `metrics/engine.py`:PRD 三·0–5 口径唯一实现;`insight/{overview,da,users,cost,text}.py` 对应四个 Tab 与 AI 洞察。
- 权限:请求头 `X-Role`(super_admin/da_admin/other)+`X-Managed-DAs`,服务端裁剪 DA 范围与导出;前端顶部「身份」仅用于本地联调,生产应由网关注入。
- 前端:**UI 设计师的设计稿代码**(React 19 + Vite + Tailwind4 + shadcn + Recharts,`frontend/src/features/*` 一 Tab 一目录),
  原本地 mock 计算已全部移除,各 Tab 通过 `frontend/src/api/*` 调后端 `/api/vm/{overview,da,users,cost}`(接口输出与设计稿 view-model 同形,比率为 0~1 小数)。
  字典(DA、数据截至日、上线日)由 `/api/insight/meta` 在启动时注入 `frontend/src/data/dict.ts`。
  设计稿与 PRD 冲突处以 PRD 为准(上线日、休眠/沉默定义、导入率分子、DA 字典、1.5 子功能)。

## 接入乙方接口(DATA_SOURCE=vendor)
接口文档见 `docs/vendor-api-spec.md`，适配器 `backend/app/vendor/vendor_adapter.py`(只做字段映射与分页，不算指标)。
```bash
DATA_SOURCE=vendor VENDOR_API_BASE_URL=http://{host}:{port} VENDOR_API_TOKEN=... \
  ./.venv/bin/uvicorn app.main:app --port 8420
```
vendor 模式下：角色只信任网关注入的 `loggedInUserId` 请求头(经乙方 `userRoleInfo` 解���)，忽略 `X-Role`；Dataset 按 `VENDOR_CACHE_TTL`(默认 300s)缓存；
`VENDOR_OTHER_IDENTITY` 决定 `identity=other` 的归属(employee/customer/test)。
测试用 `tests/vendor_fake.py` 模拟乙方服务(含分页)，并有「本地数据集→乙方响应→适配器→引擎」往返对账。

## 导出报告(PRD 4.x)
右上角「导出报告」→ 后端 `GET /api/report/html` 生成单文件 HTML：封面(分析周期/报告日期) + 洞察 / 累计 / 当期 / 分布 / 趋势 / 三率 / 使用深度 / 明细表 / 费用(仅超管与 DA 管理员)，每页 16:9，页眉带周期·范围·数据截至，页脚带口径脚注与页码；数据范围由服务端按角色裁剪。可打印另存 PDF。

## 哪些是真实的、哪些是模拟的
真实:PPT/推文生成(创建日、成功与否)、花费(元)、周度导出次数、DA/账号类型/身份(花名册+user.json)。
模拟(见 `mock_fields`):登录/激活、PubMed/大纲/内容库分享、来源标签、可用状态、开通日期、大区、SUPER 账号占比、配额、PPT 子功能、导出的日期。
注意:口径以 `docs/PRD_latest.docx` 为准。「使用」=PubMed/大纲/内容库分享/成功生成,**只登录、失败生成、纯导出都不算使用**;休眠=周期内无使用且非沉默;沉默=周期内且连续 60 天无使用、开通满 60 天;「登录未使用」=休眠/沉默账号中周期内登录过的账号(标签)。平台 07-01 上线,开通满 60 天最早 08-30,所以当前数据下沉默账号为 0。

## [TBD] 项
数据更新频率、token↔人民币换算(现直接用周报 ¥)、导出去重、点击 DA 名称是否进入下钻、海报上线(`POSTER_LIVE=1`)。
