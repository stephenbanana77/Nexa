# Nexa V2 PRD

> 从「一次性 AI 问答」到「可复用数据工作台」

---

## 一、V2 目标

V0 验证了 AI + 数据分析可行。V1 把架构升级到 LangGraph + ToolRegistry + Skill框架。V2 的目标是**让分析结果可沉淀、可复用、可追溯**。

三个核心能力：

1. **Resource Layer** — 所有产出物（数据集、图表、洞察、Notebook）都有统一 URI，Agent 和 Skill 通过 URI 引用数据，而不是传裸对象。
2. **Workflow Engine** — 一次成功的分析保存为可重复执行的工作流，换个数据集一键重跑。
3. **Observability** — 每次执行的完整轨迹：Agent plan → 每步 SQL/耗时/token/错误 → 可复盘、可重跑。

## 二、用户故事

### Story 1：分析可复用
> 我对 Superstore 数据做了一次完整的销售分析，效果很好。下次换了新的月度销售 CSV，我想一键重跑相同的分析流程，不用再手打一遍 Prompt。

### Story 2：Resource 引用
> 上次分析生成了一个 `chart://monthly-sales-trend`，这次我在 Chat 里说 "把这个图里的数据按地区拆开"，系统应该自动知道我在说哪个图、哪份数据。

### Story 3：执行透明
> Chat 里 AI 分析了 30 秒才出结果——它到底干了什么？Run History 页面展示每一步的耗时、SQL、token 消耗，出错时能定位到具体哪一步。

## 三、功能范围

### P0（V2 必须交付）

| 功能 | 说明 |
|------|------|
| **Resource Model** | 统一的 `dataset://`, `chart://`, `insight://`, `notebook://`, `connection://` URI 系统 |
| **Resource Registry** | 按 project 管理所有 Resource，支持增删查改 |
| **Workflow Model** | Workflow 数据模型：name, description, steps, triggers |
| **Workflow Runner** | 执行 Workflow 的运行时引擎，支持手动运行 |
| **Chat → Workflow** | 从一次成功的 Chat 分析生成 Workflow draft |
| **Run History** | 新增 `Run` 页面，展示执行历史：plan / skills / 每步耗时 / SQL / token |
| **Run Trace** | 单次执行的完整 trace：Agent 节点图、每步输入/输出 |
| **Skill manifest** | 将内置工具全面 Skill 化，每个有 manifest + permissions |

### P1（V2 做不了就延后）

| 功能 | 说明 |
|------|------|
| **MCP Connection MVP** | PostgreSQL / Google Sheets / Notion connector（至少 2 个） |
| **Workflow 手动编辑** | 在 Workflow 页面增删改 step |
| **Skill permission model** | Skill 白名单、数据访问范围 |
| **Skill test runner** | 在 Skills 页面直接测试 Skill 的某个 step |

### P2（V3+）

| 功能 | 说明 |
|------|------|
| Skill SDK | Python/JS SDK 开发自定义 Skill |
| Marketplace | 社区 Skill 市场 |
| Scheduler | 定时触发 Workflow |
| Multi-Agent | 多 Agent 协作 |
| 企业 RBAC | 角色权限 + SSO + 审计日志 |

## 四、V2 交付物

| 文档 | 内容 |
|------|------|
| Nexa V2 System Design.md | 系统架构图、模块关系、数据流 |
| Nexa V2 Skill Runtime Spec.md | Skill manifest 格式、executor 接口、permission 模型 |
| Nexa V2 Resource Model.md | Resource URI 规范、Registry API、引用机制 |
| Nexa V2 Workflow Engine.md | Workflow 模型、Runner 架构、Chat→Workflow 桥接 |
| Nexa V2 Execution Plan.md | 分 Phase 任务拆解、验收标准 |

## 五、成功的衡量标准

1. 做完一次 Superstore 分析 → 保存为 Workflow → 换一份新 CSV → 一键重跑得到同样结构的输出
2. Chat 里说 "基于上次的 chart://monthly-sales 按产品拆分" → Agent 正确引用历史图表
3. Run History 页面能看到最近 10 次执行，点开能看到完整的 Agent plan + SQL + 耗时
4. 系统内所有工具（execute_query, suggest_chart, run_skill 等）都通过 manifest.json 注册
