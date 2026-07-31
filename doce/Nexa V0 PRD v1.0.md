# Nexa V0 Product Requirement Document

Version: 1.0
Status: Planning

---

# 1. Product Overview（产品概述）

## Product Name

Nexa

## Product Positioning

Nexa is an AI-powered data analysis workspace.

It allows users to upload data, ask questions in natural language, and receive AI-generated analysis, visualizations, and insights.

Nexa aims to reduce the technical barrier of data analysis.

Users do not need to master:

- SQL
- Python
- Data visualization tools

They can communicate with data through natural language.

---

# 2. Vision（产品愿景）

Traditional data analysis workflow:

Data → SQL → Python → Visualization → Report

Problems:

- Requires technical skills
- Takes a long time
- Tools are fragmented

Nexa provides:

Natural Language

↓

AI Understanding

↓

Data Analysis

↓

Visualization

↓

Insight

The goal:

> Make everyone capable of discovering insights from data.

---

# 3. Target Users（目标用户）

## Primary Users

### 1. Product Managers

Problems:

- Need data insights
- Lack SQL skills
- Depend on data analysts

Nexa helps:

- Analyze user behavior
- Understand metrics
- Generate reports


---

### 2. Operations Staff

Problems:

- Handle large amounts of data
- Need frequent reports

Nexa helps:

- Analyze trends
- Find problems
- Generate summaries


---

### 3. Beginner Data Analysts

Problems:

- Learning SQL/Python
- Need assistance

Nexa helps:

- Generate SQL
- Explain data
- Speed up analysis


---

## Non-target Users

V0 does not target:

- Enterprise BI teams
- Data engineers
- Large-scale data platforms
- Real-time analytics systems

---

# 4. Core User Scenario（核心场景）

## Scenario 1: CSV Analysis

User:

"I want to understand my sales data."

Flow:

Upload CSV

↓

Nexa analyzes structure

↓

User asks:

"Why did sales decrease last month?"

↓

Nexa:

- Generates SQL
- Calculates metrics
- Creates charts
- Provides explanation

---

## Scenario 2: Database Analysis

User:

Connect MySQL database

↓

Ask:

"Which products have the highest refund rate?"

↓

Nexa:

Query database

↓

Generate:

- Table
- Chart
- Insight


---

# 5. Core User Journey（核心流程）


## First Experience

User opens Nexa

↓

Create Project

↓

Upload data

↓

AI analyzes dataset

↓

User asks questions

↓

Nexa generates insights

↓

Save analysis result


---

# 6. V0 Feature Scope

## 6.0 Authentication

Purpose:

Identify users and protect their data and API keys.

Features:

- Email + password registration
- Email + password login
- JWT-based session management
- LLM API Key management (per-user, encrypted storage)
- All LLM calls proxied through backend (frontend never accesses providers directly)

Not included:

- OAuth / SSO
- Social login (Google, GitHub)
- Team / organization accounts
- Role-based access control

## 6.1 Workspace

Purpose:

Provide the working environment.

Features:

- Home page
- Project list
- Create project
- Open project


Not included:

- Team collaboration
- Cloud sync


---

# 6.2 Project

Purpose:

Organize user's analysis work.

Contains:

- Dataset
- Chat history
- SQL
- Charts
- Reports


---

# 6.3 Data Management

Supported sources:

V0:

- CSV
- Excel
- SQLite
- MySQL


Features:

- Upload data
- Connect database
- View schema
- Preview data

Data Volume Boundaries:

V0 targets small-to-medium datasets:

| Metric | V0 Target | Notes |
|--------|-----------|-------|
| File upload (CSV/Excel) | Up to 100 MB | Files larger than 100 MB rejected with guidance |
| Row count | Up to 1,000,000 | Beyond this, DuckDB still works but frontend rendering degrades |
| Data preview | First 1,000 rows | Full dataset accessible via SQL queries |
| Connected DB (MySQL) | Tables up to 500,000 rows | Query result pagination at 1,000 rows per page |

The frontend uses virtual scrolling (ag-grid) for data tables to handle up to the preview limit smoothly. The DuckDB engine can query the full dataset regardless of preview limits.


---

# 6.4 AI Chat

Purpose:

Natural language interface.

Streaming Progress:

The analysis pipeline (understand → plan → query → analyze → visualize → insight) is transparent to the user. Each stage streams progress updates via SSE so the user sees:

- "Understanding your question..."
- "Planning analysis: sales trend, regional comparison, product breakdown"
- "Executing SQL query on 120,000 rows..."
- "Generating charts..."
- "Final insight: Sales decreased 15% in East region"

This prevents the "black box" problem where users stare at a loading spinner for 30-60 seconds with no feedback.

Examples:

User:

"Analyze sales trend"

Nexa:

- Understand intent
- Query data
- Analyze
- Explain result


---

# 6.5 SQL Assistant

Features:

- Generate SQL from natural language
- Execute SQL
- Display result


Example:

User:

"Find top 10 products"

AI generates:

SELECT...


---

# 6.6 Notebook

Support:

- Markdown
- SQL
- Python


Purpose:

Allow advanced users to manually explore data.


---

# 6.7 Visualization

Supported charts:

- Bar chart
- Line chart
- Pie chart
- Scatter chart


Features:

- AI recommends chart
- Display result
- Save chart


---

# 6.8 Insight Report

Purpose:

Convert analysis results into understandable conclusions.


Contains:

- Summary
- Charts
- Key findings
- Recommendations


---

# 7. V0 AI Capability

V0 AI Workflow:


User Question

↓

Intent Understanding

↓

Data Understanding

↓

Generate Analysis Steps

↓

Execute Data Operations

↓

Generate Visualization

↓

Generate Insight


---

# 8. Out of Scope（V0 不做）


The following features are reserved for future versions:


## Agent Platform

- Multi-agent system
- Agent marketplace


## Skill Ecosystem

- Skill SDK
- Skill marketplace


## MCP Ecosystem

- Community MCP


## Enterprise Features

- Team collaboration
- Permission system
- SSO


## Automation

- Workflow builder
- Scheduler


## Advanced Data Platform

- Data lineage
- Data governance
- Semantic layer


---

# 9. Success Metrics（成功标准）


Nexa V0 succeeds if:


A new user can:

1. Upload a dataset within 1 minute

2. Ask a question in natural language

3. Receive useful analysis within several minutes

4. Understand the generated insights


Core metric:

> Can a non-SQL user complete a data analysis task?

---

# 10. V0 Product Principle


## Simplicity First

Do one thing well:

AI-powered data analysis.


## User Intent First

Users describe goals.

They do not describe technical operations.


## Build Foundation

V0 should prepare architecture for future:

- Agent
- Skill
- MCP
- Workflow

but does not implement them fully.