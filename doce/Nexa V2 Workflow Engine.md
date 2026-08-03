# Nexa V2 Workflow Engine

---

## 一、目标

把一次成功的 Chat 分析变成可重复执行的工作流。用户不需要重新打字问 AI，点一下 Run 就能在新数据上得到同样的分析结构和输出。

---

## 二、Workflow 数据模型

```python
class Workflow(Base):
    __tablename__ = "workflows"
    
    id: UUID
    name: str
    description: str
    project_id: UUID (FK → projects)
    steps: list[WorkflowStep] (relationship)
    inputs: dict (JSON)        # 预期输入参数 {"dataset": "dataset://xxx"}
    created_from: UUID | None   # 来源 run_id 或 None（手动创建）
    version: int                # 每次编辑 +1
    status: str                 # "draft" | "active" | "archived"
    last_run_at: datetime | None
    created_at / updated_at: datetime
    created_by: UUID (FK → users)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    
    id: UUID
    workflow_id: UUID (FK → workflows)
    sort_order: int
    type: str                  # sql | skill | analyze | visualize | insight | python
    config: dict (JSON)        # 类型相关配置
    input_refs: list[str]      # ["dataset://xxx", "chart://yyy"]
    output_ref: str            # "chart://zzz"
    description: str
```

### config 按 step type

```json
// sql
{"sql_template": "SELECT category, SUM(sales) FROM {dataset} GROUP BY category", "engine": "duckdb"}

// skill  
{"skill_name": "data_summary", "params": {}}

// analyze
{"prompt": "分析以上结果的关键发现，用 Markdown 格式"}

// visualize
{"chart_type": "bar", "title": "Sales by Category"}

// insight
{"prompt": "基于数据给出 3 条业务建议"}
```

---

## 三、Workflow Runner

### 设计原则

- **幂等**：同一个 Workflow 在同一份数据上多次运行结果一致
- **隔离**：每个 step 独立执行，失败不影响已完成 step 的结果
- **可追溯**：每次运行生成完整的 Run trace
- **Resource 驱动**：所有输入输出都是 Resource URI

### Runner 接口

```python
class WorkflowRunner:
    def __init__(self, workflow: Workflow, project_id: str):
        self.workflow = workflow
        self.project_id = project_id
        self.run = None    # 当前 Run 记录
    
    async def execute(
        self, 
        inputs: dict[str, Resource],
        stream: bool = True
    ) -> AsyncGenerator[StepEvent, None]:
        """
        执行 Workflow 的所有步骤。
        
        流程：
        1. 创建 Run 记录 (status=running)
        2. 解析 input_refs → 从 ResourceRegistry 获取数据
        3. 依次执行每个 step：
           a. 创建 RunStep 记录 (status=running)
           b. 根据 type 调用对应执行器
           c. 将输出保存为 Resource
           d. 更新 RunStep (status=done, output_ref=...)
        4. 更新 Run (status=done)
        5. 返回最终结果
        """
```

### Step 执行器

```python
STEP_EXECUTORS = {
    "sql": SqlStepExecutor,         # SQL模板 → 替换变量 → execute_query
    "skill": SkillStepExecutor,    # 调用 skill_registry.execute(skill_name)
    "analyze": AnalyzeStepExecutor, # prompt → LLM → Markdown
    "visualize": VisualizeStepExecutor,  # suggest_chart + LLM fallback
    "insight": InsightStepExecutor,      # prompt → LLM → 结构化洞察
}
```

---

## 四、Chat → Workflow 桥接

### "Save as Workflow" 流程

```
用户: "分析每个地区的利润趋势"
  → Chat/Agent 执行: understand → plan → generate_sql → execute → analyze → visualize
  → 结果显示在 Chat 气泡中

用户点击 "Save as Workflow"
  → 前端 POST /api/workflows/from-run/{run_id}
  → 后端从 Run trace 提取：
      - plan steps → WorkflowStep[]
      - 每步的 SQL → sql step config
      - 每步的 prompt → analyze/insight step config
      - 使用的 dataset → input_refs
      - 产出的 chart/insight → output_refs
  → 生成 Workflow draft
  → 返回 workflow_id
  → 前端弹出 "Workflow saved" → 可跳转 Workflow 页面编辑
```

### Run Trace 转换规则

| RunStep type | → | WorkflowStep type | config 内容 |
|-------------|---|-------------------|-------------|
| generate_sql | → | sql | `{sql_template: step.sql}` |
| execute | → | （合并到前一个 sql step） | - |
| analyze | → | analyze | `{prompt: step.prompt}` |
| visualize | → | visualize | `{chart_type: "auto"}` |
| select_skill | → | skill | `{skill_name: step.skill_name}` |
| execute_skill | → | （合并到 skill step） | - |

---

## 五、Workflow API

```
GET    /api/workflows/{project_id}              # 列出 Workflow
POST   /api/workflows                           # 创建 Workflow
GET    /api/workflows/{workflow_id}             # 获取详情（含 steps）
PUT    /api/workflows/{workflow_id}             # 更新（编辑 name/steps）
DELETE /api/workflows/{workflow_id}             # 删除
POST   /api/workflows/{workflow_id}/run         # 手动运行
POST   /api/workflows/from-run/{run_id}         # Chat 分析 → Workflow draft
GET    /api/workflows/{workflow_id}/runs        # 查看执行历史
```

---

## 六、前端 Workflow 页面

```
┌─────────────────────────────────────────────────┐
│  Workflows                          [+ New]     │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │ 📋 Monthly Sales Analysis     3 steps   │    │
│  │ Created from Chat · Aug 3, 2026         │    │
│  │ Last run: ✅ 2m ago (4.2s)              │    │
│  │ [▶ Run]  [✏️ Edit]  [🗑️ Delete]          │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ 📋 Region Profit Breakdown   5 steps    │    │
│  │ Manual · Aug 2, 2026                    │    │
│  │ Never run                               │    │
│  │ [▶ Run]  [✏️ Edit]  [🗑️ Delete]          │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Workflow 编辑页面（V2 不做复杂编辑器，做列表式）

```
┌──────────────────────────────────────────────┐
│  Edit: Monthly Sales Analysis                │
│                                              │
│  Step 1 [sql]                                │
│    SELECT category, SUM(sales) ...           │
│    Input: dataset://superstore               │
│    Output: (query result)                    │
│                                       [✏️]   │
│                                              │
│  Step 2 [visualize]                          │
│    Chart type: bar                           │
│    Depends on: Step 1                        │
│    Output: chart://monthly-sales             │
│                                       [✏️]   │
│                                              │
│  Step 3 [insight]                            │
│    Prompt: "分析以上结果..."                  │
│    Depends on: Step 1, Step 2                │
│    Output: insight://monthly-analysis        │
│                                       [✏️]   │
│                                              │
│  [+ Add Step]  [💾 Save]  [▶ Run Now]        │
└──────────────────────────────────────────────┘
```

---

## 七、Workflow 与 Skill 的关系

| 维度 | Skill | Workflow |
|------|-------|----------|
| 粒度 | 标准化分析单元 | 组合多个 Skill/Step |
| 复用 | 跨项目共享 | 项目内复用 |
| 输入 | 统一参数 schema | 自由配置 |
| 创建 | 开发者/内置 | 用户从 Chat 生成 |
| 执行 | Agent 自动调用 | 用户手动触发 |

一个 Workflow 的 step 可以引用 Skill：
```json
{"type": "skill", "config": {"skill_name": "data_summary", "params": {"dataset": "dataset://xxx"}}}
```
