# Nexa 项目约定

## 架构原则

### 后端
- **数据源引擎**：所有引擎继承 `tools.query_engine.DataSourceEngine` ABC，实现 `query/preview/get_schema/get_tables`
- **Agent 工具**：通过 `agents.tools.ToolRegistry` 注册，禁止硬编码 if/else 路由
- **Agent 节点**：一个文件一个节点，`nodes/__init__.py` 只做 re-export
- **API 响应**：优先用 Pydantic model，不要裸 dict
- **配置**：LLM 相关配置统一从环境变量读取（LLM_API_KEY、LLM_BASE_URL、LLM_MODEL）

### 前端
- **设计 token**：`src/theme.ts` 是唯一色值/间距来源，禁止内联 `#0d0d0d` 等硬编码颜色
- **类型**：共享类型放 `src/types/index.ts`，页面内部私有接口可原地定义
- **API 调用**：通过 `src/services/` 模块，不要直接 `api.get()`
- **共享组件**：`DataTable`、`EmptyState` 已在 `src/components/`，新页面优先复用

### 通用
- **DeepSeek**：当前 LLM 提供商，base_url = https://api.deepseek.com/v1，model = deepseek-chat
- **SSH push**：`git@github.com:stephenbanana77/Nexa.git`，密钥在 `~/.ssh/id_ed25519`
- **编码**：CSV 上传用 chardet 自动检测，Pandas 桥接 DuckDB
