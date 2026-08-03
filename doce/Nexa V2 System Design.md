# Nexa V2 System Design

---

## 一、V2 架构全景

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  ChatPage  SkillsPage  RunHistoryPage            │
│  WorkflowPage  ResourceBrowser                   │
├─────────────────────────────────────────────────┤
│                   API Layer                      │
│  /api/chat  /api/skills  /api/resources          │
│  /api/workflows  /api/runs  /api/connections     │
├─────────────────────────────────────────────────┤
│              Agent Layer (LangGraph)              │
│  understand → plan → select_skill → execute       │
│                      ↓                           │
│              Skill Engine + Tool Registry         │
│                      ↓                           │
│              Resource Layer (URI references)      │
│         dataset://   chart://   insight://        │
│         notebook://  connection://  workflow://   │
├─────────────────────────────────────────────────┤
│            Data Layer                             │
│  DuckDB  MySQL/PostgreSQL  External APIs          │
│  (via DataSourceEngine ABC + MCP connectors)      │
└─────────────────────────────────────────────────┘
```

V2 的核心变化是中间多了一层 **Resource Layer**。Agent、Skill、Workflow 都不再直接操作 Dataset/Chart 对象，而是通过 Resource URI 引用。

---

## 二、Resource Layer

### 设计原则

- **一切皆 Resource**：数据集、图表、洞察、Notebook、Workflow、外部连接都是 Resource
- **URI 寻址**：`{type}://{id}` 格式，全局唯一
- **元数据驱动**：每个 Resource 有 name / description / tags / created_at / updated_at
- **引用透明**：Resource 可以互相引用（如 chart://x 引用 dataset://y）

### Resource 类型

| 类型 | URI 模式 | 对应实体 |
|------|----------|---------|
| dataset | `dataset://{id}` | Dataset |
| chart | `chart://{id}` | Chart |
| insight | `insight://{id}` | Insight |
| notebook | `notebook://{id}` | Notebook |
| workflow | `workflow://{id}` | Workflow |
| connection | `connection://{id}` | MySQL/PostgreSQL/API 连接 |
| table | `table://{connection_id}/{table_name}` | 外部数据库中的表 |

### Resource 模型

```
Resource {
  id: UUID
  uri: str              # "chart://abc-123"
  type: ResourceType    # dataset | chart | insight | notebook | workflow | connection | table
  name: str
  description: str
  project_id: UUID
  tags: list[str]
  metadata: JSON        # 类型相关元数据（row_count, chart_type, etc.）
  created_by: UUID
  created_at: datetime
  updated_at: datetime
}
```

### Agent 如何使用 Resource

```
用户: "用 monthly-sales 图表的数据，按地区拆分"

Agent:
  1. 解析 "monthly-sales" → ResourceRegistry.resolve("chart://monthly-sales")
  2. 获取 chart 的 metadata → 知道它来自 "dataset://superstore", SQL = "..."
  3. 构建新分析 → 生成 SQL: "SELECT region, SUM(sales) FROM (原SQL) GROUP BY region"
  4. 执行 → 返回新结果
```

---

## 三、Workflow Engine

### Workflow 模型

```
Workflow {
  id: UUID
  name: str
  description: str
  project_id: UUID
  steps: list[WorkflowStep]
  inputs: JSON         # 预期输入参数
  created_from: UUID   # 来源（Chat 分析 / 手动创建）
  version: int
  created_at / updated_at
}

WorkflowStep {
  id: UUID
  workflow_id: UUID
  sort_order: int
  type: str            # sql | skill | analyze | visualize | insight | python | transform
  config: JSON         # 类型相关配置（SQL模板、Skill名称、prompt等）
  input_refs: list[str]  # 引用的 Resource URI
  output_ref: str      # 产出的 Resource URI
}
```

### Workflow Runner

Workflow 运行时引擎负责按照 step 顺序执行：

```
1. 加载 Workflow 定义
2. 解析 input_refs → 从 ResourceRegistry 获取数据
3. 依次执行每个 step：

   sql step:     config.sql_template → 替换变量 → execute_query
   skill step:   config.skill_name → skill_registry.execute()
   analyze step: config.prompt → LLM 分析 → 返回文本
   visualize:    suggest_chart(上一步结果) → 返回 chart_config

4. 每个 step 的结果存入 RunTrace
5. 最终结果保存为新的 Resource
```

### Chat → Workflow 桥接

```
Chat 分析完成后：
  → 前端 "Save as Workflow" 按钮
  → 后端提取 Agent plan + 各 step 的 SQL/prompt
  → 生成 Workflow draft
  → 用户可在 Workflow 页面编辑和保存
```

---

## 四、Observability — Run History

### Run 模型

```
Run {
  id: UUID
  type: str            # "chat" | "skill" | "workflow"
  ref_id: UUID         # conversation_id / skill_execution_id / workflow_id
  project_id: UUID
  status: str           # "running" | "done" | "failed"
  plan: JSON            # Agent plan steps
  started_at / finished_at
  duration_ms: int
  token_estimate: int   # 估算 token 消耗
}

RunStep {
  id: UUID
  run_id: UUID
  sort_order: int
  type: str             # sql | skill | analyze | visualize
  input_summary: str
  output_summary: str
  sql: str | None
  error: str | None
  duration_ms: int
  started_at / finished_at
}
```

### Run History 页面

```
┌─────────────────────────────────────────────────┐
│  Run History                          [刷新]     │
├─────────────────────────────────────────────────┤
│  📊 Chat Analysis    32s ago    ✅ 3.2s  1.2K tk │
│  📈 Skill: 数据概览    2m ago    ✅ 5.1s  0.8K tk │
│  🔄 Workflow: Sales   10m ago   ❌ Step 2 failed │
│  📊 Chat Analysis    1h ago     ✅ 2.1s  0.9K tk │
├─────────────────────────────────────────────────┤
│  点击展开 Run Trace:                              │
│  understand (0.3s) → plan (0.2s) → select_skill  │
│  (0.8s) → execute_skill (4.2s)                   │
│    ├ sql: "SELECT CORR(a,b)..." (2.1s) ✅        │
│    ├ visualize: bar chart (0.5s) ✅              │
│    └ insight: markdown analysis (1.6s) ✅        │
│  总耗时: 5.3s | Token 估算: ~1,200               │
└─────────────────────────────────────────────────┘
```

---

## 五、MCP Runtime

### 设计

V2 不建完整的 MCP 生态系统，而是先做 2-3 个官方 Connector：

1. **PostgreSQL** — 基于 PyMySQL 模式扩展
2. **Local Files** — 浏览和导入本地 CSV/Excel/JSON
3. **Google Sheets** — 通过 API 读取在线表格

每个 Connector 实现 `DataSourceEngine` 接口，注册到 `EngineRegistry`。

Connector 作为 `connection://` Resource 暴露，Agent 可以通过 URI 引用：

```
用户: "连上我的 production_db"
  → 创建 connection://prod-pg Resource

用户: "分析 table://prod-pg/orders 的月度趋势"
  → Agent 解析 URI → 找到 connection → 获取 schema → 生成 SQL → 查询
```

---

## 六、数据流总结

```
Chat/Skill Analysis 完成
  │
  ├─→ Resource Layer: 保存产出为 Resource (chart://, insight://)
  │
  ├─→ Workflow Engine: 提取 steps → 生成 Workflow draft
  │
  └─→ Run History: 记录完整 trace (plan + 每步耗时 + SQL + token)
```

三者互相关联：
- Workflow 的每个 step 引用 Resource
- Run History 记录 Workflow 执行过程  
- Resource 记录数据来源（哪个 Workflow 产出的）
