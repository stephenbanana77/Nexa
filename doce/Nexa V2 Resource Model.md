# Nexa V2 Resource Model

---

## 一、设计哲学

> Everything is a Resource. Every Resource has a URI.

当前问题：Dataset、Insight、Chart、Notebook 各自为政。Agent 和 Skill 直接操作 SQLAlchemy 模型对象，耦合严重。

V2 方案：所有分析产出物都通过 **Resource URI** 寻址。Agent 说 "给我 chart://monthly-sales 的数据来源" 而不是 "给我这个 Chart 对象的 Insight 的 SQL"。

---

## 二、Resource URI 规范

```
{type}://{project_id}/{resource_id}

示例:
  dataset://proj-123/dataset-456
  chart://proj-123/chart-789
  insight://proj-123/insight-012
  notebook://proj-123/nb-345
  workflow://proj-123/wf-678
  connection://proj-123/conn-901
  table://proj-123/conn-901/orders
```

**简写形式**（同一 project 内）：
```
chart://chart-789
```

---

## 三、Resource 数据结构

```python
class ResourceType(str, Enum):
    DATASET = "dataset"
    CHART = "chart"
    INSIGHT = "insight"
    NOTEBOOK = "notebook"
    WORKFLOW = "workflow"
    CONNECTION = "connection"
    TABLE = "table"

class ResourceRef:
    """引用一个 Resource，而非持有其内容"""
    uri: str
    type: ResourceType
    name: str

class Resource(ResourceRef):
    """完整的 Resource，包含元数据和内容"""
    id: UUID
    project_id: UUID
    description: str
    tags: list[str]
    metadata: dict        # 类型相关元数据
    content: dict         # 实际数据（懒加载）
    created_at: datetime
    updated_at: datetime
    created_by: UUID
```

### metadata 按类型

```python
# dataset://
{"row_count": 9994, "column_count": 21, "source_type": "csv", "file_path": "..."}

# chart://
{"chart_type": "bar", "title": "Monthly Sales", "dataset_ref": "dataset://xxx", "sql": "SELECT ..."}

# insight://
{"summary": "Top 5 categories...", "key_findings": [...], "dataset_ref": "dataset://xxx", "chart_refs": ["chart://yyy"]}

# notebook://
{"cell_count": 5, "cells": [{"type": "markdown", "preview": "## Analysis..."}]}

# workflow://
{"step_count": 3, "last_run": "2026-08-03T10:00:00Z", "last_status": "done"}

# connection://
{"host": "localhost", "port": 5432, "database": "analytics", "engine": "postgresql"}

# table://
{"row_count": 100000, "column_count": 15, "connection_ref": "connection://xxx"}
```

---

## 四、ResourceRegistry API

```python
class ResourceRegistry:
    def register(resource: Resource) -> Resource
    def get(uri: str) -> Resource | None
    def resolve(uri_or_name: str) -> Resource | None       # 模糊匹配（名称或 URI）
    def list(project_id: str, type: ResourceType | None = None) -> list[Resource]
    def search(project_id: str, query: str) -> list[Resource]
    def delete(uri: str) -> None
    def get_references(resource: Resource) -> list[Resource] # 获取引用链
    def get_referrers(resource: Resource) -> list[Resource]   # 获取被引用链
```

### 后端 API

```
GET    /api/resources/{project_id}              # 列出所有 Resource
GET    /api/resources/{project_id}?type=chart   # 按类型过滤
GET    /api/resources/detail/{uri}              # 获取单个 Resource 详情
GET    /api/resources/references/{uri}          # 获取引用链
POST   /api/resources/resolve                   # 模糊解析 {"query": "monthly sales"}
DELETE /api/resources/{uri}                     # 删除 Resource
```

---

## 五、集成点

### Agent 集成

```
用户: "用 monthly-sales 的数据，按产品拆分"

Agent 的 select_skill 节点：
  1. 解析 "monthly-sales" 
  2. resource_registry.resolve("monthly-sales")
     → Resource(uri="chart://chart-789", type=chart, metadata={sql: "SELECT ...", dataset_ref: "dataset://456"})
  3. 获取源 dataset → get_schema("dataset://456")
  4. 生成新 SQL → 执行 → 保存新 chart://Resource
```

### Skill 集成

Skill 的 inputs/outputs 用 Resource 取代裸 dict：

```json
{
  "inputs": {
    "dataset": {"type": "resource", "resource_type": "dataset"}
  },
  "outputs": {
    "chart": {"type": "resource", "resource_type": "chart"},
    "insight": {"type": "resource", "resource_type": "insight"}
  }
}
```

### Workflow 集成

Workflow step 的 `input_refs` 和 `output_ref` 都是 Resource URI：

```json
{
  "steps": [
    {
      "type": "sql",
      "input_refs": ["dataset://superstore"],
      "output_ref": "chart://monthly-trend",
      "config": {"prompt": "按月聚合销售额"}
    }
  ]
}
```

---

## 六、与现有模型的映射

| 现有 SQLAlchemy Model | 对应 Resource | 转换逻辑 |
|----------------------|---------------|---------|
| `Dataset` | `dataset://{id}` | 直接映射 |
| `Chart` | `chart://{id}` | 补充 dataset_ref、sql |
| `Insight` | `insight://{id}` | 补充 dataset_ref、chart_refs |
| `Notebook` | `notebook://{id}` | 补充 cell_count |
| （新建）`Workflow` | `workflow://{id}` | 新建模型 |
| （新建）`Connection` | `connection://{id}` | 新建模型 |

**转换时机**：执行 `resource_registry.register()` 时，从对应 SQLAlchemy 模型提取元数据生成 Resource。

---

## 七、Resource 生命周期

```
创建 ─→ 更新 ─→ 归档（软删除）
  │                │
  └─ 被引用 ←──────┘（删除前检查引用链）
```

- 删除 Resource 前检查 `get_referrers()`，如果被 Workflow 或其他 Resource 引用则警告。
- Resource 不可变——每次分析产出新的 Resource，不覆盖已有 Resource。
- 同一次分析的多个产出（chart + insight）通过 `run_id` 关联。
