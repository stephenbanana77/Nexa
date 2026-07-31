# Nexa V0 System Design

Version: 1.0

Status: Planning


---

# 1. Overview


## Product

Nexa is an AI-powered data analysis workspace.

The system allows users to:

- Upload datasets
- Ask questions using natural language
- Generate AI-assisted analysis
- Create visualizations
- Save analysis insights


The goal of Nexa V0:

> Enable users without advanced SQL or programming skills to complete data analysis tasks through natural language.


---

# 2. System Scope


## V0 Supported Capabilities


### Data Input

- CSV
- Excel
- SQLite
- MySQL


### Analysis

- Natural language questions
- SQL generation
- Data querying
- Statistical analysis
- Visualization generation
- Insight generation


### User Workspace

- Project management
- Conversation history
- Dataset management
- Analysis result storage



---

# 3. System Components


The Nexa V0 system consists of:


```
Nexa

├── Frontend Application

├── Backend Service

├── AI Analysis System

├── Data Processing System

├── Storage System

└── External Services

    └── LLM Provider

```


---

# 4. High-Level System Flow


```
User

↓

Frontend

↓

Backend API

↓

AI Analysis System

↓

Data Processing System

↓

Storage / External Data Source

↓

Analysis Result

↓

Frontend Display

```


---

# 5. Frontend System Design


## Responsibility


The frontend provides user interaction.


It is responsible for:

- User interface
- Project navigation
- Data visualization
- Chat interaction
- Result presentation


The frontend does not handle:

- AI reasoning
- Database operations
- Data analysis logic



---

# 6. Frontend Modules


```
Frontend

├── Authentication

├── Home

├── Project Workspace

│
├── Overview Page

├── Data Page

├── Chat Page

├── SQL Page

├── Notebook Page

└── Insights Page


└── Settings

```


---

## Chat ↔ Notebook Bridge

Chat and Notebook are not isolated tools — they form a progressive workflow:

```
Chat (Natural Language)
│
├── AI generates analysis
│
├── User sees results inline (table, chart, text)
│
└── User clicks "Open in Notebook"
      │
      └── Notebook auto-populates with:
            ├── Markdown cell: context description
            ├── SQL cell: the generated query
            └── Python cell: the visualization code
```

This bridge gives power users the ability to refine AI-generated analysis while keeping the simple path for non-technical users. The Notebook page displays all Notebooks created from Chat conversations within the current project.

Notebook Export API:

```
POST /api/chat/{message_id}/export-to-notebook
```

Response:

```json
{
  "notebook_id": "nb_001",
  "cells": [
    {"type": "markdown", "content": "Analysis: Sales decline investigation"},
    {"type": "sql", "content": "SELECT region, SUM(sales)..."},
    {"type": "python", "content": "import matplotlib..."}
  ]
}
```



---

# 7. Backend System Design


## Responsibility


The backend is the application coordination layer.


Responsibilities:

- Receive frontend requests
- Manage business logic
- Coordinate AI services
- Manage datasets
- Store analysis results


---

# 8. Backend Modules


```
Backend

├── Auth Service

├── User Service

├── Project Service

├── Dataset Service

├── Chat Service

├── Analysis Service

├── Insight Service

└── File Service

```


---

# 9. API Design


## Project API


### Create Project


Endpoint:

```
POST /api/projects
```


Request:


```json
{
  "name": "Sales Analysis"
}
```


Response:


```json
{
  "id": "project_001",
  "name": "Sales Analysis"
}
```



---

## Dataset API


### Upload Dataset


Endpoint:


```
POST /api/datasets/upload
```


Flow:


```
Frontend

↓

Backend

↓

File Storage

↓

Dataset Metadata Creation

↓

AI Data Understanding

```


---

## Auth API

### Register

Endpoint:

```
POST /api/auth/register
```

Request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "id": "user_001",
  "email": "user@example.com",
  "token": "eyJhbG..."
}
```

### Login

Endpoint:

```
POST /api/auth/login
```

Request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "token": "eyJhbG..."
}
```

### API Key Management

Endpoint:

```
POST /api/auth/api-key
```

Request:

```json
{
  "provider": "openai",
  "key": "sk-..."
}
```

API Keys are stored encrypted in PostgreSQL. The frontend never accesses LLM providers directly — all LLM calls are proxied through the backend, which decrypts and attaches the user's API key.



---

## Chat API


Endpoint:


```
POST /api/chat
```


Request:


```json
{
  "project_id": "project_001",
  "message": "Why did sales decrease?"
}
```


Response:


```json
{
  "answer": "Sales decreased mainly in East region",
  "charts": [],
  "insights": []
}
```


---

## Chat Stream API (SSE)

Endpoint:

```
POST /api/chat/stream
```

Request (same as non-streaming):

```json
{
  "project_id": "project_001",
  "message": "Why did sales decrease?"
}
```

Response is a stream of SSE events:

```
event: understanding
data: {"message": "Understanding your question...", "progress": 10}

event: planning
data: {"message": "Planning analysis: 1) Sales trend 2) Regional comparison 3) Product analysis", "progress": 20}

event: sql_generating
data: {"message": "Generating SQL query...", "progress": 30}

event: querying
data: {"message": "Executing query on 120,000 rows...", "progress": 50}

event: analyzing
data: {"message": "Analyzing results...", "progress": 70}

event: visualizing
data: {"message": "Generating charts...", "progress": 85}

event: insight
data: {"message": "Sales decreased 15%, mainly in East region", "progress": 95, "charts": [...], "insights": [...]}

event: done
data: {"progress": 100}

event: error
data: {"message": "Failed to generate SQL: column 'revenue' not found", "code": "SQL_ERROR"}
```

The frontend renders progress indicators based on SSE events. Each event updates the chat UI with intermediate status, keeping the user informed throughout the analysis pipeline.



---

# 10. AI Analysis System Design


## Responsibility


The AI system is responsible for:


- Understanding user intent
- Planning analysis steps
- Selecting tools
- Executing analysis
- Generating explanations



---

# 11. AI System Architecture


```
User Question

↓

Agent Controller

↓

Context Manager

↓

Task Understanding

↓

Tool Executor

↓

Analysis Result

↓

LLM Generation

↓

Final Response

```


---

# 12. Agent Controller


## Responsibility


The Agent Controller manages the AI reasoning process.


Functions:


- Receive user requests
- Understand intent
- Decide next actions
- Call analysis tools



Example:


User:


```
Why did sales decrease?
```


Agent:


```
Need:

1. Analyze sales trend

2. Compare regions

3. Find abnormal products

```



---

# 13. Context Manager


## Responsibility


Maintain analysis context.


Stores:


- Conversation history
- Current project
- Dataset information
- Previous results



Example:


```
Project:

Sales Analysis


Dataset:

sales.csv


Previous Analysis:

Monthly sales trend

```



---

# 14. Prompt Manager


## Responsibility


Manage AI instructions.


Includes:


- System prompts
- Task prompts
- Analysis templates


Example:


```
You are an AI data analyst.

Analyze the dataset and explain findings.

```


---

# 15. Tool Executor


## Responsibility


Execute analysis capabilities.


V0 Tools:


```
Tool Executor

├── SQL Generator

├── SQL Runner

├── Data Analyzer

└── Chart Generator

```


Execution:


```
User Question

↓

Agent

↓

Tool Executor

↓

Data Source

↓

Result

```



---

# 16. Data Processing System


## Responsibility


Manage data ingestion and analysis.


Components:


```
Data System

├── Data Loader

├── Schema Analyzer

├── Query Engine

└── Data Processor

```


---

# 17. Data Loader


Responsibilities:


- Receive uploaded files
- Parse datasets
- Store files
- Create metadata



Supported:


- CSV
- Excel
- SQLite
- MySQL



---

# 18. Schema Analyzer


Automatically analyze dataset structure.


Detect:


- Column names
- Data types
- Missing values
- Basic statistics



Example:


```
sales

type:

number


date

type:

datetime


region

type:

category

```



---

# 19. Query Engine


Responsibilities:


- Execute SQL
- Retrieve data
- Return results



Example:


Generated SQL:


```sql
SELECT
region,
SUM(sales)
FROM orders
GROUP BY region;
```


---

# 20. Storage Design


## Database Storage


Stores:


```
User

Project

Dataset

Conversation

Message

Insight

Chart

```

### Insight Content Model

Insights generated by AI are structurally irregular — they may contain:

- Natural language summaries
- Data tables
- Multiple charts
- SQL queries
- Key findings and recommendations

Storing them as fixed relational columns is impractical. Instead, Insight uses a flexible JSON content field:

```json
{
  "id": "insight_001",
  "project_id": "project_001",
  "question": "Why did sales decrease last month?",
  "content": {
    "summary": "Sales decreased 15% in July, primarily driven by East region (-20%)...",
    "key_findings": [
      "East region: -20% (main contributor)",
      "Product A revenue dropped 35%",
      "New competitor entered East market in June"
    ],
    "tables": [
      {
        "title": "Monthly Sales by Region",
        "columns": ["region", "jun_sales", "jul_sales", "change"],
        "data": [
          ["East", 500000, 400000, "-20%"],
          ["North", 300000, 310000, "+3%"]
        ]
      }
    ],
    "charts": [
      {"type": "line", "config": {}, "chart_id": "chart_001"},
      {"type": "bar", "config": {}, "chart_id": "chart_002"}
    ],
    "sql_queries": [
      "SELECT region, SUM(sales) FROM orders WHERE month='July' GROUP BY region"
    ],
    "recommendations": [
      "Investigate East region supply chain issues",
      "Review Product A pricing strategy"
    ]
  },
  "created_at": "2026-07-31T12:00:00Z"
}
```

Charts referenced in the Insight content are stored as separate Chart entities (for reuse across insights), but their rendering configuration is embedded in the Insight content for self-contained display.


---

## File Storage


Stores:


- Uploaded datasets
- Generated reports
- Export files



---

## Vector Storage


Future:


- Dataset semantic search
- Knowledge retrieval
- Document understanding


Not required in V0.



---

# 21. Database Entity Relationship


```
User

 |

 |

Project

 |

 |----------------

 |               |

Dataset      Conversation

                 |

                 |

              Message


Project

 |

 |

Insight

 |

 |

Chart

```



---

# 22. Core Analysis Workflow


Example:


User:

```
Analyze sales decline
```


System:


```
Frontend

↓

Backend API

↓

Agent Controller

↓

Context Manager

↓

Task Understanding

↓

Tool Executor

↓

SQL Generation

↓

Query Engine

↓

Data Result

↓

LLM Analysis

↓

Insight Generation

↓

Frontend Display

```



---

# 23. Error Handling Design


## Data Error


Example:

Invalid CSV format


Handling:


- Detect error
- Return explanation
- Suggest correction



---

## SQL Error


Example:

Invalid query


Handling:


- Capture error
- Retry generation
- Explain problem



---

## LLM Error


Example:

Model unavailable


Handling:


- Retry request
- Fallback response



---

# 24. Security Considerations


V0:


- API key protection
- File access isolation
- User project isolation


Future:


- Permission system
- Enterprise security
- Audit logs



---

# 25. Future Evolution


The V0 architecture prepares for:


## Orchestrator


Upgrade Agent Controller into a full planning system.


## Skill System


Replace internal tools with reusable skills.


## MCP System


Connect external services.


## Workflow Engine


Automate analysis pipelines.



Future:


```
Orchestrator

↓

Agent Runtime

↓

Skill Runtime

↓

MCP Runtime

↓

Resource Manager

↓

External World

```



---

# 26. System Design Principles


## Modularity

Each module should have clear responsibility.


---

## Extensibility

Future capabilities should be easy to add.


---

## Separation of Concerns


Frontend:

User experience


Backend:

Business logic


AI:

Reasoning


Data:

Data processing


---

## Progressive Complexity


V0:

Simple and usable.


Future:

More intelligent and autonomous.



---

# 27. V0 Final Goal


Nexa V0 succeeds when:


A user can:


```
Upload Data

↓

Ask Question

↓

AI Understands

↓

AI Analyzes

↓

Generate Insight

↓

Save Result

```


without requiring advanced programming knowledge.



---

# End

