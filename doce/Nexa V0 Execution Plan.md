# Nexa V0 Execution Plan

Version: 1.0
Status: Ready

---

## 批次概览

| Phase | 名称 | 核心产出 | 预计产出物 |
|-------|------|---------|-----------|
| 0 | 骨架 | 项目脚手架、Docker 环境 | 三个容器能通信 |
| 1 | 地基 | Auth、数据上传、建表 | 能注册/登录/上传 CSV |
| 2 | 数据 | DuckDB 查询、Schema 分析 | 看到数据预览、AI 理解 schema |
| 3 | AI 核心 | Agent Controller、SQL 生成、SSE | 能提问、能生成分析 |
| 4 | 可视化 | ECharts、Chat 结果展示 | 图表嵌入对话、Insight 可保存 |
| 5 | 闭环 | Notebook、Chat↔Notebook 桥接 | 高级用户可手动修改代码 |

**Phase 0-1** 做完 → 能看到上传的 CSV 数据
**Phase 2-3** 做完 → 核心功能闭环（用户提问 → AI 分析 → 得到答案）
**Phase 4-5** 做完 → 完整 V0 体验

---

## Phase 0: 项目骨架

### 目标

三个容器（前端/后端/数据库）能启动，前后端能互相通信。

### 任务

- [ ] 初始化前端项目：`npm create vite@latest frontend -- --template react-ts`
- [ ] 安装前端依赖：antd / ag-grid-community / echarts / zustand / axios
- [ ] 初始化后端项目：FastAPI 入口文件 + 目录结构
- [ ] 安装后端依赖：fastapi / uvicorn / sqlalchemy / alembic / duckdb / pandas / sse-starlette / python-jose / passlib[bcrypt] / python-multipart
- [ ] 编写 `docker-compose.yml`：frontend / backend / postgres 三个 service
- [ ] 编写各服务的 `Dockerfile`
- [ ] 编写 Nginx 配置文件
- [ ] 后端写一个 `/api/health` 健康检查接口
- [ ] 前端写一个简单的 Hello 页面，调 health 接口确认通路

### 验收标准

```
docker-compose up

→ localhost:3000 打开前端页面
→ 前端调用 /api/health 返回 {"status": "ok"}
```

---

## Phase 1: 地基（Auth + 数据上传）

### 目标

用户能注册/登录，能上传 CSV 文件，数据存入 PostgreSQL。

### 任务

#### Auth

- [ ] 创建 PostgreSQL 数据库 `nexa`
- [ ] Alembic 初始化，创建 users 表迁移
- [ ] UserService：注册（hash 密码）、登录（验证 + 签发 JWT）
- [ ] Auth Middleware：JWT 验证依赖注入
- [ ] API Key 管理：加密存储/解密读取，提供 CRUD 接口
- [ ] 前端：注册页、登录页、登录状态管理（Zustand）

#### 数据上传

- [ ] 创建 projects / datasets 表（Alembic 迁移）
- [ ] FileService：接收 CSV/Excel 上传，存储到本地 `storage/` 目录
- [ ] DatasetService：创建 dataset 记录、记录元数据（文件名/大小/行数）
- [ ] 前端：项目列表页、创建项目、项目内上传数据页

### 验收标准

```
1. 注册新用户 → 登录 → 进入项目列表
2. 创建项目 "Sales Analysis"
3. 上传 sales.csv
4. 数据库中出现对应的 user / project / dataset 记录
```

---

## Phase 2: 数据引擎（DuckDB + Schema 分析）

### 目标

上传的 CSV 能被自动分析结构，前端能看到数据预览。

### 任务

- [ ] SchemaAnalyzer：读 CSV → 用 Pandas 检测列名、类型、缺失值、基本统计
- [ ] 更新 datasets 表：存储 schema 分析结果（列信息 JSON）
- [ ] DataLoader：将 CSV 注册到 DuckDB 虚拟表
- [ ] QueryEngine：执行 SQL 查询，返回结果集
- [ ] 前端 Data 页面：
  - Dataset summary（行数/列数/来源/时间）
  - Schema 表格（列名 + 类型 + 缺失率）
  - Data Preview（ag-grid 展示前 1000 行，虚拟滚动）

### 验收标准

```
上传 sales.csv（12 万行）
→ Data 页面自动显示：
  - 15 columns, 120,000 rows
  - Schema 表格：date(datetime) / sales(number) / region(string) ...
  - 数据预览：前 1000 行，可滚动，不卡顿
→ 手动 SQL 查询能跑通（预留给 Phase 5）
```

---

## Phase 3: AI 核心（Agent + SQL 生成 + SSE）

### 目标

用户在 Chat 里提问题，AI 理解意图 → 生成 SQL → 执行 → 流式返回分析结果。

### 任务

#### Agent Controller

- [ ] LLM Client：OpenAI Compatible 封装，支持配置 base_url + api_key
- [ ] PromptManager：系统提示词模板（"你是一个数据分析师..."）
- [ ] ContextManager：注入当前项目的 dataset schema 到 prompt
- [ ] AgentController：接收用户问题 → 调用 LLM → 解析意图 → 选择工具

#### Tool Executor

- [ ] SQLGenerator：LLM 根据 schema + 用户问题生成 SQL
- [ ] SQLRunner：执行生成的 SQL（走 DuckDB QueryEngine）
- [ ] DataAnalyzer：LLM 分析查询结果，生成文字解释

#### SSE 流式响应

- [ ] ChatService：分析流程编排
- [ ] SSE Endpoint：`POST /api/chat/stream`，按阶段推送事件
  - understanding → planning → sql_generating → querying → analyzing → done/error
- [ ] 前端 Chat 页面：对话输入、SSE EventSource 监听、进度条组件

### 验收标准

```
在项目内打开 Chat
→ 输入："分析最近一个月销售下降的原因"
→ 进度条实时显示当前阶段
→ 30-60 秒后返回分析结果：文字解释 + 可能的数据表格
→ 可以追问："华东地区为什么最严重？"（上下文连续对话）
```

---

## Phase 4: 可视化 + Insight 闭环

### 目标

AI 分析结果附带图表，Insight 可以保存和回溯。

### 任务

#### 图表生成

- [ ] ChartGenerator：LLM 根据数据推荐图表类型 + 生成 ECharts 配置
- [ ] 前端 Chart 组件：接收 ECharts config，渲染交互式图表
- [ ] 图表嵌入 Chat 消息中展示

#### Insight 保存

- [ ] 创建 insights / charts 表（Alembic 迁移）
- [ ] InsightService：保存 insight（JSON content）、关联 project
- [ ] ChartService：保存图表配置
- [ ] 前端 Insights 页面：Insight Card 列表（问题/摘要/图表数/时间）
- [ ] Insight 详情：展开查看完整分析结果（文字 + 图表 + SQL）

### 验收标准

```
Chat 中问："各区域销售额对比"
→ 返回文字 + 一张柱状图
→ 点击 "Save Insight"
→ Insights 页面出现新的 Insight Card
→ 点击 Card 查看完整内容（含图表和 SQL）
→ 回到 Chat，历史消息仍在
```

---

## Phase 5: Notebook + Chat 桥接

### 目标

高级用户可以从 Chat 结果一键跳转到 Notebook，手动修改 SQL/Python。

### 任务

#### Notebook

- [ ] Notebook 数据模型：project 下多个 notebook，notebook 下多个 cell
- [ ] Cell 类型：Markdown / SQL / Python
- [ ] SQL Cell：编辑器 + 执行按钮 + 结果表格展示
- [ ] Python Cell：Python 沙箱执行（可选 Pyodide 或后端执行）
- [ ] Markdown Cell：编辑 + 渲染预览

#### Chat → Notebook 桥接

- [ ] Export API：`POST /api/chat/{message_id}/export-to-notebook`
- [ ] 前端 Chat 消息底部 [📓 Open in Notebook] 按钮
- [ ] 点击后自动创建/跳转到 Notebook，填充：
  - Markdown cell：分析上下文
  - SQL cell：AI 生成的 SQL
  - Python cell：ECharts 配置代码

### 验收标准

```
Chat 分析完成后
→ 点击 "Open in Notebook"
→ 跳转到 Notebook 页面
→ 自动填充了 3 个 cell（markdown / sql / python）
→ 手动修改 SQL，点击执行，看到新结果
→ 将修改后的结果保存为新 Insight
```

---

## 依赖关系

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
                                        │                         │
                                        └──── 串行依赖 ──────────┘
```

所有 Phase 严格串行——后一个依赖前一个的产物。Phase 1 依赖 Phase 0 的 Docker 环境和数据库；Phase 2 依赖 Phase 1 的数据上传能力；Phase 3 依赖 Phase 2 的 Schema 分析和 DuckDB 引擎；Phase 4 依赖 Phase 3 的 AI 分析输出；Phase 5 依赖 Phase 4 的 Chat 消息结构。

---

## 关键决策记录

| 决策 | 理由 |
|------|------|
| Phase 3 之前不做 Notebook | 没有 AI 分析结果，Notebook 是空的，没价值 |
| SSE 和 Agent 放在同一个 Phase | SSE 是 Agent 执行的"展示层"，分开做需要 Mock，反而增加工作量 |
| 不做 AI 自动建 Notebook | V0 的用户不会描述"帮我建一个 Notebook"，他们只会描述"帮我分析销售数据" |
| Phase 0 就搭好 Docker | 环境问题越早解决越好，不要等开发到一半再容器化 |
