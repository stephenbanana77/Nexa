# Nexa V2 Execution Plan

---

## Phase 概览

| Phase | 名称 | 核心产出 | 依赖 |
|-------|------|---------|------|
| 0 | 文档 | PRD + System Design + Specs | 无 |
| 1 | Resource Layer | Resource 模型 + Registry + API | Phase 0 |
| 2 | Run History | Run/RunStep 模型 + RunHistory API + 前端页面 | Phase 0 |
| 3 | Workflow Engine | Workflow/WorkflowStep 模型 + Runner + API + 前端页面 | Phase 1 |
| 4 | Chat → Workflow | Save as Workflow 按钮 + 前端/后端集成 | Phase 2, 3 |
| 5 | MCP Connections | PostgreSQL + Google Sheets connector | Phase 1 |
| 6 | 全文 Skill 化 | 内置工具按 manifest 注册 + Permission 模型 | Phase 1 |

---

## Phase 1：Resource Layer（4-6h）

### 目标
所有分析产出物都有统一 URI，Agent 通过 URI 引用数据。

### 任务

- [ ] **新建 `backend/models/resource.py`**
  - `ResourceType` enum（dataset/chart/insight/notebook/workflow/connection/table）
  - `Resource` SQLAlchemy model（id, uri, type, name, description, project_id, tags, metadata, created_at, updated_at）

- [ ] **新建 `backend/resources/registry.py`**
  - `ResourceRegistry` 类（register, get, resolve, list, search, delete, get_references, get_referrers）
  - 从现有 Dataset/Chart/Insight/Notebook 自动生成 Resource 的迁移函数

- [ ] **新建 `backend/api/resources.py`**
  - `GET /api/resources/{project_id}` — 列表
  - `GET /api/resources/detail/{uri}` — 详情
  - `GET /api/resources/references/{uri}` — 引用链
  - `POST /api/resources/resolve` — 模糊搜索
  - `DELETE /api/resources/{uri}` — 删除

- [ ] **更新创建逻辑**
  - `api/insights.py` saveInsight → 同时 `resource_registry.register(insight_as_resource)`
  - `api/projects.py` upload dataset → 同时注册 dataset resource
  - Chat agent 保存 chart → 同时注册 chart resource

### 验收标准
- API 返回 `GET /api/resources/proj-xxx?type=chart` 能列出项目所有图表
- `POST /api/resources/resolve` 输入 `{"query": "monthly"}` 返回匹配的 Resource

---

## Phase 2：Run History + Observability（4-6h）

### 目标
每次 Agent/Skill/Workflow 执行都有可追溯的完整轨迹。

### 任务

- [ ] **新建 `backend/models/run.py`**
  - `Run` model（id, type, ref_id, project_id, status, plan, started_at, finished_at, duration_ms, token_estimate）
  - `RunStep` model（id, run_id, sort_order, type, input_summary, output_summary, sql, error, duration_ms）

- [ ] **新建 `backend/services/run_tracker.py`**
  - `create_run()` / `add_step()` / `update_step()` / `complete_run()`
  - 在 AgentController.run() 中嵌入 trace 逻辑
  - 在 SkillRegistry.execute() 中嵌入 trace 逻辑

- [ ] **新建 `backend/api/runs.py`**
  - `GET /api/runs/{project_id}` — 列表
  - `GET /api/runs/{run_id}` — 详情（含 steps）
  - `POST /api/runs/{run_id}/rerun` — 重新运行某一步（V2 P1）

- [ ] **前端：新建 `RunHistoryPage.tsx`**
  - 列表：type icon + 名称 + 时间 + 耗时 + status badge
  - 展开面板：step 列表 + SQL + 错误信息

- [ ] **前端：嵌套在 ProjectPage**
  - 新增 "History" Tab

### 验收标准
- 做一次 Chat 分析 → 切到 History Tab → 看到刚完成的 Run
- 点开 Run → 看到 Agent plan 每一步 + SQL + 耗时

---

## Phase 3：Workflow Engine（6-8h）

### 目标
用户可以把成功分析保存为可重复执行的工作流。

### 任务

- [ ] **新建 `backend/models/workflow.py`**
  - `Workflow` 和 `WorkflowStep` model（见 Workflow Engine 文档）

- [ ] **新建 `backend/workflows/runner.py`**
  - `WorkflowRunner` 类，支持流式执行
  - `STEP_EXECUTORS` 字典（sql/skill/analyze/visualize/insight 执行器）

- [ ] **新建 `backend/api/workflows.py`**
  - CRUD + Run + From-Run 端点

- [ ] **前端：新建 `WorkflowPage.tsx`**
  - 列表：卡片式，每个 Workflow 显示 step 数 + 上次运行状态
  - [Run] [Edit] [Delete] 操作

- [ ] **前端：`WorkflowEditPage.tsx`**（简化版）
  - 列表式编辑（不拖拽）
  - step 增删 + config 编辑
  - 实时预览 Run 结果

- [ ] **前端：嵌套在 ProjectPage**
  - 新增 "Workflows" Tab

### 验收标准
- 手动创建一个 3-step Workflow → Run → 看到 3 个 step 依次执行
- step 产出自动注册为 Resource

---

## Phase 4：Chat → Workflow 桥接（2-3h）

### 目标
Chat 分析完成后一键保存为 Workflow。

### 任务

- [ ] **后端：`POST /api/workflows/from-run/{run_id}`**
  - 从 Run trace 提取 steps → 生成 Workflow draft

- [ ] **前端：Chat 气泡增加 "Save as Workflow" 按钮**
  - 调用 from-run API → 弹窗确认 → 可跳转 Workflow 页面

### 验收标准
- Chat 分析完成 → 点 "Save as Workflow" → Workflow 列表出现新 draft

---

## Phase 5：MCP Connections（4-6h）

### 目标
2 个官方 Connector：PostgreSQL + Google Sheets。

### 任务

- [ ] **`backend/connections/postgresql.py`**
  - PostgreSQLConnector 继承 DataSourceEngine
  - 实现 query/preview/schema/tables/health_check

- [ ] **`backend/connections/googlesheets.py`**
  - GoogleSheetsConnector（需 Google API 凭证）
  - 读取 Sheet 数据，映射为 table Resource

- [ ] **`backend/api/connections.py`**
  - `POST /api/connections` — 创建连接
  - `GET /api/connections/{project_id}` — 列表
  - `DELETE /api/connections/{id}` — 删除

- [ ] **前端：复用 MySQLConnectModal 模式**
  - PostgreSQL 连接表单
  - Google Sheets 连接（输入 Sheet URL + API Key）

### 验收标准
- 连接 PostgreSQL → 看到表列表 → 在 Chat 里 "分析 table://pg-conn/orders" → AI 生成 SQL 查询

---

## Phase 6：全文 Skill 化（2-3h）

### 目标
所有内置工具都用 manifest 格式注册，统一 permission 模型。

### 任务

- [ ] 为 `execute_query` / `get_schema` / `suggest_chart` 编写 manifest.json
- [ ] 更新 `skill_registry` 以 manifest 格式注册内置工具
- [ ] 更新 SkillCard 前端展示 manifest 的 inputs/outputs
- [ ] Skill 执行时校验 permissions

### 验收标准
- Skills 页面能看到所有内置工具的 manifest 详情
- 执行 Skill 时，permission 不符合的逻辑被拦截

---

## 不改的文件

- `backend/services/auth.py`
- `backend/api/auth.py`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/NotFoundPage.tsx`
- Docker 相关文件

---

## 时间估算

| Phase | 预计时间 | 关键依赖 |
|-------|---------|---------|
| Phase 1: Resource Layer | 4-6h | 无 |
| Phase 2: Run History | 4-6h | Phase 1 |
| Phase 3: Workflow Engine | 6-8h | Phase 1, 2 |
| Phase 4: Chat → Workflow | 2-3h | Phase 2, 3 |
| Phase 5: MCP Connections | 4-6h | Phase 1 |
| Phase 6: 全文 Skill 化 | 2-3h | Phase 1 |

**总计：22-32h**（可在 3-4 天内完成）

---

## 风险

| 风险 | 缓解 |
|------|------|
| Resource Layer 与现有模型耦合 | 不改现有模型，Resource 作为新表 + 迁移脚本自动生成 |
| Workflow Runner 复杂度 | 先做线性执行（无分支/条件），不引入 DAG |
| MCP Connector 的凭证安全 | 复用 ApiKey 模型的加密方式 |
