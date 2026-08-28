# Nexa 数据工作台开发蓝图

> 文档状态：Draft v1.0  
> 目标：为 Nexa 后续产品、架构和工程开发提供统一方向，避免围绕零散功能持续堆叠。

## 1. 产品定位

Nexa 是一个面向个人分析师和小型业务团队的可信数据工作台。它帮助用户把原始数据转化为经过质量检查、口径确认、可复现并且可共享的业务结论。

Nexa 不是通用 AI 聊天工作台，也不是只负责画图的 BI 工具。AI 是工作台中的协作能力，核心产品价值是：

```text
数据接入 -> 数据质量 -> 指标治理 -> 分析执行 -> 证据审计 -> 报告发布 -> 权限共享
```

产品判断标准不是“能不能回答一句话”，而是：

- 用户是否能在较短时间内得到业务上可用的答案；
- 答案是否有明确的数据来源、指标口径和计算过程；
- 另一个人是否可以复核、复用和继续追问；
- 数据发生变化后，结论是否可以重新执行并发现变化。

## 2. 首要用户与首个场景

### 2.1 目标用户

第一阶段聚焦以下用户，不追求覆盖所有企业场景：

- 业务分析师、运营、销售、财务人员；
- 有 Excel、CSV、Google Sheets 或数据库数据，但没有完整数据团队的小型组织；
- 需要频繁回答经营问题并交付周报、复盘或管理层简报的人。

### 2.2 首个可验证场景

用户上传一份真实业务数据，在 10 分钟内完成：

1. 预览数据并确认字段；
2. 查看数据质量问题；
3. 确认关键指标和维度口径；
4. 提问销售额、利润率、趋势、排行和异常等问题；
5. 查看 SQL、结果样本和数据来源；
6. 发布一份带证据的可复核报告。

这是 V1 的核心验收场景。其他功能只有在不破坏这个闭环的情况下加入。

## 3. 产品原则与明确边界

### 3.1 原则

1. **可信优先**：不能解释来源和口径的结论，不作为已发布结论。
2. **工作流优先**：聊天、Skill 和自动化都服务于数据工作流。
3. **可复现**：保存问题、Schema 快照、SQL、策略判定、结果摘要和报告版本。
4. **人机协作**：AI 可以提出定义和结论，人负责审批关键口径和发布结果。
5. **渐进扩展**：先把小规模真实数据做透，再扩展到团队和外部生态。

### 3.2 不在 V1 做的事

- 通用聊天机器人和开放式 Agent 市场；
- 大型数仓、复杂 ETL 或实时流处理平台；
- 没有沙箱和权限隔离的任意 Python 执行；
- 只追求视觉效果的仪表盘模板；
- 在核心数据契约尚未稳定前建设开放式 MCP Marketplace。

## 4. 核心用户闭环

```mermaid
flowchart LR
    A[创建项目] --> B[接入数据源]
    B --> C[预览与质量检查]
    C --> D[定义指标和维度]
    D --> E[审批数据口径]
    E --> F[发起分析任务]
    F --> G[Agent 选择 Skill]
    G --> H[生成安全查询]
    H --> I[执行并生成图表]
    I --> J[形成证据链]
    J --> K[人工复核]
    K --> L[发布报告]
    L --> M[权限共享与复用]
    M --> F
```

每个环节都要产生可追踪状态，而不是只返回一次性 JSON：

- 数据源：连接状态、最近同步时间、凭据引用；
- 数据集：版本、Schema、行数和来源；
- 质量检查：检查项、严重级别、运行时间和处理状态；
- 指标：定义、SQL、Owner、审批状态和生效版本；
- 分析任务：问题、输入资产、执行步骤和耗时；
- 证据：SQL、策略判定、结果样本、Schema 哈希和引用关系；
- 报告：草稿、审核、发布和归档版本；
- 共享：成员、角色、资源范围和访问日志。

## 5. 产品信息架构

工作台以项目为顶层边界，页面和 API 都围绕数据资产组织：

```text
Project
├── Data Sources
│   └── Datasets / Dataset Versions
├── Data Quality Checks
├── Semantic Layer
│   ├── Metrics
│   └── Dimensions
├── Analysis Runs
│   ├── Questions
│   ├── SQL Attempts
│   └── Evidence
├── Reports
├── Skills
├── MCP Connectors
└── Members / Permissions
```

聊天入口仍然保留，但必须能够明确关联当前项目、数据集、指标和最近分析，而不是脱离上下文的独立对话。

## 6. 系统架构

```text
React 工作台
  ├─ 项目 / 数据 / 质量 / 语义层 / 分析 / 报告 / 共享
  └─ Chat 与实时运行状态（SSE）
          |
FastAPI API 层
  ├─ Project & Permission Service
  ├─ Data Source Service
  ├─ Data Quality Service
  ├─ Semantic Layer Service
  ├─ Analysis & Run Tracker
  ├─ Report & Evidence Service
  └─ Skill / MCP Registry
          |
Agent Orchestrator（LangGraph）
  ├─ Understand / Plan
  ├─ Capability and permission check
  ├─ Skill selection and execution
  ├─ SQL generation / policy / retry
  └─ Analyze / visualize / compose
          |
Data and Extension Layer
  ├─ DataSourceEngine（DuckDB / PostgreSQL / MySQL / Sheets）
  ├─ MCP Client Runtime
  ├─ Skill Runtime
  └─ Background Job Queue
          |
Persistence and Governance
  ├─ Project assets and versions
  ├─ Run lineage and evidence
  ├─ Credentials reference
  └─ Audit logs
```

现有的 FastAPI、LangGraph、DuckDB、SQL 安全策略、运行血缘和语义层可以作为基础继续演进。后续开发应优先稳定领域契约，而不是先增加更多 UI 页面。

## 7. Skill、MCP 与 Agent 的职责边界

```text
MCP：连接外部系统和数据源
Skill：封装一项可复用的数据工作能力
Agent：根据问题、权限和上下文编排 MCP 与 Skill
```

### 7.1 MCP

MCP 负责标准化外部能力接入，例如：

- PostgreSQL：Schema、表、只读查询、采样；
- Google Sheets：表格读取、版本信息和范围采样；
- 文件存储：CSV、Excel、Parquet 读取；
- 后续的 CRM、广告平台或业务 API。

MCP Runtime 必须包含：连接生命周期、能力发现、超时、重试、权限检查、凭据引用、调用审计和错误归一化。普通数据库连接器不能直接宣称为 MCP Connector。

### 7.2 Skill

Skill 负责数据工作流程，例如：

- 数据概览和质量检查；
- 利润率和亏损产品分析；
- 趋势、环比和异常分析；
- 排行、贡献度和结构分析；
- 指标契约检查；
- 报告、决策简报和后续问题生成。

Skill Manifest 至少要声明：输入资源、输出资源、步骤、所需读取权限、写入权限、网络权限、LLM 权限、版本和可否被 Agent 调用。Python、HTTP、Notebook 等高风险步骤默认关闭，必须经过显式授权和隔离运行。

### 7.3 Agent

Agent 只做编排和解释，不绕过治理层：

1. 识别用户意图和所需资产；
2. 检查数据集、指标审批状态和权限；
3. 选择 Skill 或生成 SQL；
4. 经过 SQL Policy 和执行成本检查；
5. 记录完整运行血缘；
6. 生成带证据的结果；
7. 在无法回答时明确说明缺少什么，而不是编造结论。

## 8. 核心领域模型

以下模型是后续数据库和 API 设计的稳定边界：

| 模型 | 关键字段 | 状态或版本要求 |
|---|---|---|
| Project | owner、name、settings | active / archived |
| DataSource | type、config_ref、status、last_checked_at | connected / degraded / disconnected |
| Dataset | source_id、table_name、schema_hash、row_count | active / stale / archived |
| DatasetVersion | dataset_id、version、schema、storage_ref | immutable |
| QualityCheck | dataset_version、checks、blocking_count | passed / warning / failed |
| Metric | name、definition、sql、owner | draft / approved / rejected |
| Dimension | name、definition、column、owner | draft / approved / rejected |
| AnalysisRun | question、dataset_version、metric_versions | running / succeeded / failed |
| Evidence | run_id、sql、policy、sample、schema_hash | immutable |
| Report | run_ids、sections、reviewer、published_at | draft / published / archived |
| Skill | manifest、version、permissions | enabled / disabled |
| MCPConnector | server、capabilities、config_ref | active / paused / error |
| Membership | project_id、user_id、role | active / revoked |

关键原则：数据集版本、指标版本、证据和已发布报告不可原地覆盖。更新应生成新版本，保证历史报告仍然可以复核。

## 9. V1、V2、V3 开发路线

### V1：个人可信分析工作台

**目标**：一个人可以从真实文件或表格得到可信报告。

**范围**：

- CSV、Excel、Google Sheets 接入；
- 数据预览、Schema、质量检查和问题提示；
- 指标和维度定义、审批和版本；
- 5-8 个高频数据分析 Skill；
- Agent 问答、SQL 安全、图表和证据链；
- 报告草稿、复核和发布；
- 本地 Demo、运行历史和离线评测。

**验收标准**：

- 首次用户可在 10 分钟内完成一次完整闭环；
- 常见经营问题成功率不低于 90%；
- 结果准确率不低于 95%；
- 常见问题平均出结果时间不超过 2 分钟；
- 已发布报告的 SQL、Schema 和数据集版本可复核；
- 阻断性质量问题或未审批指标不能发布报告。

### V2：小团队协作工作台

**目标**：分析资产可以被团队共同维护和安全使用。

**范围**：

- 项目成员、角色和资源级权限；
- 报告只读共享、评论、审核和版本；
- 数据源凭据安全存储和连接健康检查；
- 定时分析、任务队列和失败重试；
- PostgreSQL、MySQL、Google Sheets 的真实连接验证；
- 指标 Owner、变更审批和影响范围提示。

**验收标准**：

- Viewer 无法执行查询或修改指标；
- 数据源凭据不出现在前端、日志和证据中；
- 定时任务在服务重启后不会重复发布或丢失状态；
- 报告共享链接只暴露授权范围内的内容。

### V3：可扩展数据工作平台

**目标**：外部连接器和团队分析能力可以持续扩展。

**范围**：

- MCP Client Runtime 和官方 Connector；
- Skill 安装、版本、依赖和团队 Skill 库；
- MCP/Skill 权限审批、沙箱和调用审计；
- 多租户隔离、后台任务和可观测性；
- 生产级 Notebook 沙箱；
- Agent 质量评测和成本监控。

## 10. 工程实施顺序

开发顺序按“能力闭环”而不是按页面拆分：

1. **稳定契约**：补齐领域模型、状态机、版本和统一错误结构。
2. **打通 V1 主路径**：以 CSV/Excel + DuckDB 为默认路径，完成接入到发布的端到端验收。
3. **补齐 Skill Runtime**：统一 Manifest、参数校验、权限、超时、执行记录和输出资源。
4. **接入第一个真实外部源**：优先 PostgreSQL，验证凭据、Schema、查询和失败恢复。
5. **实现团队治理**：权限、共享、审批、审计和版本不可变性。
6. **实现 MCP Runtime**：在数据契约和权限模型稳定后接入 Google Sheets 等 Connector。
7. **建立效率评测**：用真实任务比较人工流程与 Nexa 流程的耗时、准确率、复核时间和复用率。

每个阶段都必须包含前端流程、后端 API、数据迁移、测试、运行记录和文档，不接受只完成一个孤立按钮的“功能完成”。

## 11. 安全、治理与可靠性要求

- 默认只允许只读、单语句和有行数上限的查询；
- SQL 执行前进行 AST 策略检查和必要的 dry-run / EXPLAIN；
- 外部凭据只保存加密引用，禁止进入浏览器响应和运行日志；
- Skill 的 HTTP、Python、Notebook 能力默认禁用；
- MCP 调用必须有超时、取消、重试上限和审计事件；
- 所有已发布报告引用不可变的 DatasetVersion、MetricVersion 和 Evidence；
- 数据源、分析任务和报告都要有可观测的状态、错误和耗时；
- 多用户场景必须在查询执行、资源读取和报告共享三层都做权限检查。

## 12. 质量与评测体系

测试不能只验证接口返回 200，需要覆盖真实业务任务：

- 数据接入：编码、空文件、超大文件、Schema 漂移；
- 质量检查：缺失、重复、负值、类型错误和异常值；
- 指标治理：定义不完整、字段不存在、未审批和版本变化；
- Agent：SQL 正确率、拒答正确率、重试次数和延迟；
- Skill：输入校验、权限拒绝、失败恢复和输出结构；
- MCP：连接失败、超时、凭据泄露和重复调用；
- 报告：证据完整性、发布门禁和权限访问；
- 效率：完成任务时间、人工复核时间、结果准确率和重复使用意愿。

每次影响 Agent、SQL、Skill 或数据源的改动，都应通过离线评测和至少一个端到端业务案例。

## 13. 当前代码与目标的对应关系

当前仓库已经具备的基础：

- LangGraph Agent 和 SQL 安全策略；
- DuckDB 文件数据分析；
- 基础 MySQL / PostgreSQL / Google Sheets 连接器；
- 数据质量检查；
- Semantic Layer 和指标审批；
- Run Lineage、Evidence 和报告发布门禁；
- Manifest-based Skill MVP。

当前仍然缺少或需要产品化的部分：

- 完整的数据源连接管理和凭据安全存储；
- 真正的 MCP Client Runtime，而不只是普通连接器；
- Skill 的参数化、依赖、版本和高风险执行隔离；
- 团队成员、角色权限和报告共享；
- 后台任务、定时执行和多 worker 状态一致性；
- 基于真实用户任务的效率评测。

## 14. 近期决策

在下一轮开发开始前，必须确认以下决策：

1. V1 默认数据路径是“文件 + DuckDB”，外部数据源作为可选增强；
2. 首个外部 MCP Connector 优先选择 PostgreSQL；
3. 首批 Skill 围绕经营分析，而不是泛化到所有 AI 能力；
4. 报告发布必须依赖质量检查和指标审批；
5. 权限和证据模型先于开放式 Skill/MCP 市场；
6. 每个新增能力必须有真实业务任务和可量化验收指标。

只要以上方向不改变，后续实现就可以围绕一条稳定主线推进：

> 让用户用最少的数据准备和复核成本，得到可信、可解释、可复用的业务分析结果。
