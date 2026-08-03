# Nexa V2 Skill Runtime Spec

---

## 一、Skill Manifest 规范

每个 Skill 必须有一个 `manifest.json`，定义元数据和执行契约。

### manifest.json 结构

```json
{
  "name": "data_summary",
  "title": "数据概览",
  "description": "自动生成数据集的整体统计概览",
  "version": "1.0.0",
  "category": "statistics",
  "icon": "BarChartOutlined",
  "author": "Nexa",
  
  "inputs": {
    "dataset": {
      "type": "resource",
      "resource_type": "dataset",
      "required": true,
      "description": "要分析的数据集"
    }
  },
  
  "outputs": {
    "summary": {
      "type": "resource",
      "resource_type": "insight",
      "description": "分析结果洞察"
    },
    "chart": {
      "type": "resource", 
      "resource_type": "chart",
      "description": "概览图表"
    }
  },
  
  "permissions": {
    "read": ["schema", "data"],
    "write": ["insight", "chart"],
    "network": false,
    "llm": true
  },
  
  "agent_callable": true,

  "steps": [
    {
      "id": "generate_stats",
      "type": "sql",
      "prompt": "生成数据集整体统计：行数、列类型、缺失值、数值分布..."
    },
    {
      "id": "overview_chart",
      "type": "visualize",
      "chart": "bar",
      "depends_on": ["generate_stats"]
    },
    {
      "id": "summary_insight",
      "type": "insight",
      "prompt": "总结数据概览：规模、数据质量、分布特征、建议...",
      "depends_on": ["generate_stats", "overview_chart"]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 唯一标识符，snake_case |
| `title` | string | ✅ | 人类可读名称 |
| `description` | string | ✅ | 1-2 句描述 |
| `version` | string | ✅ | 语义化版本 |
| `category` | string | ✅ | statistics / analysis / cleaning / forecast / visualization |
| `inputs` | object | ✅ | 输入参数契约 |
| `outputs` | object | ✅ | 输出产物契约 |
| `permissions` | object | ✅ | 权限声明 |
| `agent_callable` | boolean | ✅ | Agent 能否自动调用 |
| `steps` | array | ✅ | 执行步骤 |

---

## 二、Step 类型规范

### sql

```json
{
  "id": "step_1",
  "type": "sql",
  "prompt": "SQL 生成提示词模板，支持 {variable} 占位",
  "depends_on": ["previous_step_id"]
}
```

执行流程：`prompt → LLM → SQL → execute_query → 返回结果`

### visualize

```json
{
  "id": "step_2", 
  "type": "visualize",
  "chart": "bar",
  "depends_on": ["step_1"]
}
```

chart 可选值：`bar | line | pie | scatter | heatmap | auto`

`auto` 表示由 `suggest_chart` 根据数据自动选择。

### insight

```json
{
  "id": "step_3",
  "type": "insight",
  "prompt": "分析提示词",
  "depends_on": ["step_1", "step_2"]
}
```

执行流程：`将前序步骤结果注入 prompt → LLM → Markdown 分析文本`

### python

```json
{
  "id": "step_4",
  "type": "python",
  "code": "import pandas as pd\nresult = df.describe()",
  "depends_on": ["step_1"]
}
```

V2 阶段 Python 执行需要沙箱环境（Docker 或 restricted eval）。

### transform

```json
{
  "id": "step_5",
  "type": "transform",
  "operation": "pivot | filter | sort | group | merge",
  "config": {},
  "depends_on": ["step_1"]
}
```

常用数据转换操作的声明式定义。

---

## 三、Executor 接口

```python
class SkillExecutor:
    def __init__(self, skill_manifest: dict):
        self.manifest = skill_manifest
        self.steps = skill_manifest["steps"]
    
    async def execute(
        self, 
        project_id: str, 
        inputs: dict[str, Resource],
        stream: bool = True
    ) -> AsyncGenerator[StepEvent, None]:
        """
        执行 Skill 的所有步骤。
        
        每步产出 StepEvent:
        - step_start: {"step_id": "...", "type": "sql"}
        - step_progress: {"step_id": "...", "message": "..."}
        - step_done: {"step_id": "...", "output": {...}}
        - step_error: {"step_id": "...", "error": "..."}
        - skill_done: {"outputs": {"summary": "insight://...", "chart": "chart://..."}}
        """
```

### Resource 集成

每个 step 的输入/输出都是 Resource：

```
Step input:  Resource("dataset://abc-123", type=dataset, data={...})
Step output: Resource("chart://def-456", type=chart, data={...})
```

这确保 Skill 执行结果可以：
1. 被 ResourceRegistry 索引
2. 被后续 Workflow step 引用
3. 在 Run History 中追溯

---

## 四、Permission 模型

```json
{
  "permissions": {
    "read": ["schema", "data"],
    "write": ["insight", "chart"],
    "network": false,
    "llm": true
  }
}
```

| 权限 | 说明 |
|------|------|
| `read.schema` | 读取数据集 schema |
| `read.data` | 读取数据内容 |
| `write.insight` | 创建 Insight Resource |
| `write.chart` | 创建 Chart Resource |
| `network` | 是否需要外部网络访问 |
| `llm` | 是否需要调用 LLM |

Agent 调用 Skill 时，根据 permission 声明检查该 Skill 是否能安全执行。

---

## 五、内置工具 Skill 化

V2 目标：所有 `agents/tools.py` 中的工具都通过 manifest 注册。

| 工具 | 对应 Skill | agent_callable |
|------|-----------|----------------|
| `execute_query` | sql_executor | true |
| `get_schema` | schema_inspector | true |
| `suggest_chart` | chart_generator | true |

工具 Skill 化后的好处：
- 统一的权限声明
- 可追溯的执行记录
- 可组合到 Workflow 中
- 可被其他 Skill 的 step 引用
