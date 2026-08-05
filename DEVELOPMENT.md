# Nexa 开发指南

## 快速开始

### 环境要求

- Python 3.12+ (推荐 3.13)
- Node.js 22+
- PostgreSQL 16 (可选，开发可用 SQLite)

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选，有默认值）
cp ../.env.example ../.env
# 编辑 .env 填入你的 LLM_API_KEY

# 初始化数据库（开发模式自动用 SQLite）
python main.py
# 访问 http://localhost:8000/docs 查看 API 文档
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

### Docker 一键启动

```bash
docker compose up --build
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# PostgreSQL: localhost:5432
```

---

## 开发工作流

### 运行测试

```bash
# 后端
cd backend
pytest tests/ -v

# 前端
cd frontend
npx vitest run
```

### 数据库迁移

```bash
cd backend
# 修改 models/ 后生成迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# Docker 部署时会自动 migrate
```

### 代码检查

```bash
# 前端
cd frontend && npm run lint
```

### Git 规范

```
分支命名: feat/xxx, fix/xxx, docs/xxx
提交格式: type(scope): message

示例:
feat(agent): 添加 SQL 自纠错循环
fix(api): 修复搜索路由 crash
docs: 更新开发指南
```

---

## 项目结构

```
backend/
├── api/           # FastAPI 路由 (11 个)
├── agents/        # LangGraph Agent 系统
│   ├── nodes/     # 7 个 pipeline 节点
│   ├── prompts.py # LLM prompt 模板
│   └── tools.py   # Agent 工具 + SQL 安全
├── models/        # SQLAlchemy 数据模型 (6 个文件)
├── skills/        # Skill 运行时 + 注册表
├── connections/   # 数据源连接器 (PG, MySQL, GSheets)
├── resources/     # 资源注册表
├── services/      # 认证 + Run 追踪
├── tests/         # 测试套件 (8 个文件)
└── utils/         # 配置

frontend/src/
├── pages/         # 13 个页面组件
├── components/    # 6 个共享组件
├── api/           # Axios 客户端
├── stores/        # Zustand 状态管理
└── types/         # TypeScript 类型
```

---

## 关键架构决策

1. **DuckDB** 作为默认查询引擎，内存执行，无需额外部署
2. **LangGraph** 编排 Agent pipeline：understand→plan→select_skill→sql→execute→analyze→visualize→compose
3. **SQL 安全层** 拦截 DROP/DELETE/TRUNCATE，自动加 LIMIT 10000
4. **资源注册表** 统一 URI 引用所有产物 (dataset:// chart:// insight://)
5. **双数据库** 开发用 SQLite，生产环境变量切换到 PostgreSQL

## 常见问题

### Q: 后端启动报 import 错误？
确保在 `backend/` 目录下运行，并且安装了所有依赖：
```bash
cd backend && pip install -r requirements.txt
```

### Q: 前端请求 401？
检查 `.env` 文件中 SECRET_KEY 是否与后端一致。

### Q: Docker 启动后前端访问后端 502？
检查 docker-compose 中 CORS_ORIGINS 是否包含前端地址。
