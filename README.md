# Nexa

AI-powered data analysis workspace. Upload data, ask questions in natural language, and get AI-generated analysis, visualizations, and insights — no SQL or Python required.

> **Goal:** Make everyone capable of discovering insights from data.

---

## Features

| Feature | Description |
|---------|-------------|
| **Natural Language Analysis** | Ask questions like "Why did sales drop last month?" and get AI-powered answers |
| **Multi-source Data** | Upload CSV, Excel, SQLite, or connect to MySQL databases |
| **SQL Assistant** | Generate and execute SQL from natural language prompts |
| **Auto Visualization** | AI recommends the best charts (bar, line, pie, scatter) |
| **Notebook** | Manual exploration with Markdown, SQL, and Python cells |
| **Streaming Progress** | Real-time SSE updates so you know what the AI is doing |
| **Project Management** | Organize datasets, conversations, charts, and reports per project |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19 + TypeScript + Vite |
| **UI** | Ant Design + ag-grid-community |
| **Charts** | Apache ECharts |
| **State** | Zustand |
| **Backend** | Python + FastAPI |
| **Auth** | JWT + bcrypt |
| **Streaming** | Server-Sent Events (SSE) |
| **AI API** | OpenAI-compatible (OpenAI, DeepSeek, Claude, local models) |
| **Data Engine** | DuckDB + Pandas |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy + Alembic |
| **Deployment** | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

### Run with Docker

```bash
git clone https://github.com/stephenbanana77/Nexa.git
cd Nexa
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server: http://localhost:5173

---

## Project Structure

```
Nexa/
├── frontend/           # React + TypeScript frontend
│   ├── src/
│   │   ├── components/ # Reusable UI components
│   │   ├── pages/      # Route pages
│   │   ├── api/        # API client
│   │   ├── stores/     # Zustand state stores
│   │   └── assets/     # Static assets
│   ├── package.json
│   └── vite.config.ts
│
├── backend/            # FastAPI backend
│   ├── api/            # API routes (auth, projects, chat, etc.)
│   ├── models/         # SQLAlchemy database models
│   ├── services/       # Business logic
│   ├── agents/         # AI agent controller
│   ├── tools/          # Data processing tools
│   ├── database/       # DB connection & base models
│   ├── utils/          # Utilities
│   ├── storage/        # Uploaded files
│   ├── main.py         # App entry point
│   └── requirements.txt
│
├── doce/               # Product docs (PRD, tech spec, architecture)
├── docker-compose.yml  # Full-stack Docker setup
└── README.md
```

---

## Data Volume Limits (V0)

## V2 Features

- **Skill System**: 7 built-in skills with JSON manifest + runtime registry
- **Workflow Engine**: save analysis as reusable pipeline, edit steps, rerun
- **Resource Layer**: URI-based registry (dataset:// chart:// insight://)
- **Run History**: full pipeline trace with 6-step tracking
- **Dashboard**: auto-generated from saved insights
- **Global Search**: search across projects, datasets, insights, workflows
- **SQL Safety**: auto-LIMIT, DROP/DELETE interception, confidence scoring
- **Export**: CSV download + Markdown copy from chat

## Quick Links

- [Development Guide](./DEVELOPMENT.md)
- [API Docs](http://localhost:8000/docs) (after starting backend)


| Metric | Limit |
|--------|-------|
| File upload (CSV/Excel) | Up to 100 MB |
| Row count | Up to 1,000,000 |
| Data preview | First 1,000 rows |
| Connected DB tables | Up to 500,000 rows |
| Query result pagination | 1,000 rows per page |

---

## Environment Variables

Backend `.env`:

```env
DATABASE_URL=postgresql://nexa:nexa@localhost:5432/nexa
SECRET_KEY=your-secret-key
STORAGE_PATH=./storage
```

> **Note:** LLM API keys are managed per-user in the app (encrypted in DB, proxied through backend).

---

## Roadmap

| Version | Focus |
|---------|-------|
| **V0** | Core data analysis + AI chat + visualization | ✅ |
| **V1** | Agent memory, RAG, advanced data understanding | ✅ |
| **V2** | Skill system, MCP runtime, workflow engine | ✅ |
| **V3** | Multi-agent collaboration, marketplace, enterprise | 🔜 |

---

## License

MIT
