# Nexa V0 Tech Stack Design

Version: 1.0

Status: Planning


---

# 1. Overview


## Product

Nexa is an AI-powered data analysis workspace.

The purpose of V0 is to provide users with an AI-assisted data analysis experience:

- Upload data
- Ask questions using natural language
- Generate analysis
- Create visualizations
- Produce insights


---

## Technology Selection Goals


The technology stack should satisfy:


### 1. Fast Development

Enable rapid MVP development.


### 2. AI Compatibility

Support:

- LLM integration
- Data processing
- Agent development


### 3. Data Capability

Support:

- Structured data
- SQL analysis
- Visualization


### 4. Future Extensibility

Prepare for:

- Agent Runtime
- Skill System
- MCP Ecosystem
- Workflow Automation



---

# 2. Overall Technology Architecture


```
                         User

                          |

                          v


                 Frontend Application


                          |

                          v


                    Backend API


                          |

          --------------------------------

          |                              |

          v                              v


      AI Service                  Data Service


          |                              |

          v                              v


     LLM Provider              Database / Storage


```


---

# 3. Frontend Technology Stack


## 3.1 Framework


Recommended:

```
React + TypeScript
```


Reason:


- Mature ecosystem
- Strong support for AI applications
- Suitable for complex workspace products
- Large component ecosystem


Alternative:


```
Vue 3 + TypeScript
```


Reason:

- Faster development
- Suitable for small teams


---

# 3.2 Build Tool


Recommended:


```
Vite
```


Reason:


- Fast development server
- Modern frontend tooling
- Simple configuration



---

# 3.3 UI Framework


Recommended:


```
Ant Design
```


Usage:


- Tables
- Forms
- Navigation
- Dashboard components


Reason:


- Enterprise application style
- Suitable for data platforms


Alternative:


```
shadcn/ui
```


Reason:


- Modern SaaS design
- More customizable



---

# 3.4 Visualization


Recommended:


```
Apache ECharts
```


Used for:


- Line charts
- Bar charts
- Scatter plots
- Data dashboards


Reason:


- Powerful data visualization capability
- Large ecosystem
- Suitable for analytical applications



---

# 3.5 State Management


Recommended:


```
Zustand
```


Responsible for:


- User state
- Project state
- Chat state
- Application state



---

# 3.6 Large Data Table Rendering

Recommended:

```
@tanstack/react-virtual
```

Used for:

- Data preview tables
- Query result display
- Large dataset browsing

Reason:

Ant Design Table renders all rows into DOM by default. For datasets with thousands or tens of thousands of rows, this causes severe performance degradation. Virtual scrolling only renders visible rows in the viewport, keeping the DOM lightweight.

Alternative:

```
ag-grid-community
```

Reason:

- Purpose-built for data-heavy tables
- Built-in virtual scrolling, sorting, filtering
- Better for analytical workloads than Ant Design Table

Decision for V0:

Use Ant Design for application chrome (navigation, forms, cards).
Use ag-grid-community for data preview and query result tables.



---

# 4. Backend Technology Stack


# 4.1 Programming Language


Recommended:


```
Python 3.11+
```


Reason:


Python ecosystem:


- AI
- Data analysis
- Machine learning
- Automation



---

# 4.2 Backend Framework


Recommended:


```
FastAPI
```


Responsibilities:


- API service
- Request handling
- Authentication
- Service coordination


Reasons:


- High performance
- Async support
- AI ecosystem friendly
- Simple development



---

# 4.3 Authentication

Recommended:

```
JWT + bcrypt
```

Libraries:

```
python-jose (JWT)
passlib[bcrypt] (password hashing)
```

Responsibilities:

- User registration and login
- Token issuance and verification
- API route protection
- API Key management for LLM providers

Reason:

JWT is stateless and works well with FastAPI's dependency injection. API Keys are stored encrypted in PostgreSQL and proxied through the backend — the frontend never directly accesses LLM providers. This prevents key leakage and allows usage tracking.

API Key Flow:

```
Frontend
↓
Backend API (validates JWT)
↓
Backend proxies to LLM (attaches decrypted API Key)
↓
LLM Provider
```

---

# 4.4 Streaming Response (SSE)

Recommended:

```
Server-Sent Events (SSE)
```

Library:

```
sse-starlette
```

Used for:

- AI analysis progress streaming
- SQL generation progress
- Tool execution status updates
- Chart generation feedback

Reason:

Data analysis is not instant. The full pipeline (intent understanding → SQL generation → query execution → analysis → visualization) can take 30 seconds to several minutes. Without streaming progress, users perceive the system as broken or unresponsive.

SSE over WebSocket for V0:

SSE is simpler — unidirectional server-to-client, built on HTTP, no extra protocol negotiation. WebSocket is overkill for V0 where only the server pushes progress updates. Future collaborative features may require WebSocket upgrade.

Streaming Event Types:

| Event | Description |
|-------|-------------|
| `understanding` | AI is understanding the question |
| `planning` | AI is planning analysis steps |
| `sql_generating` | AI is generating SQL |
| `querying` | Executing data query |
| `analyzing` | Analyzing query results |
| `visualizing` | Generating charts |
| `insight` | Generating final insight |
| `done` | Analysis complete |
| `error` | Error occurred with message |



---

# 5. AI Layer Technology


# 5.1 LLM Integration


Recommended:


```
OpenAI Compatible API
```


Support:


- OpenAI
- DeepSeek
- Claude
- Local Models


Reason:


Unified interface.


Example:


```
Application

↓

LLM Client

↓

Different Models

```



---

# 5.2 Agent Architecture


## V0


Do not introduce complex Agent frameworks.


Use:


```
Custom Agent Controller
```


Architecture:


```
User Request

↓

Agent Controller

↓

Prompt

↓

Tool Calling

↓

Result

↓

Response

```


Reason:


- Easier understanding
- Easier debugging
- Full control



---

# 5.3 Future Agent Framework


Future versions:


```
LangGraph
```


Used for:


- Multi-agent
- Workflow
- State management
- Complex reasoning



---

# 6. Data Processing Stack


# 6.1 Data Processing Library


Recommended:


```
Pandas
```


Used for:


- CSV processing
- Data cleaning
- Data transformation
- Statistics



---

# 6.2 Analytical SQL Engine


Recommended:


```
DuckDB
```


Reason:


DuckDB is designed for analytical workloads.


Advantages:


- Fast local analytics
- SQL support
- Excellent CSV support


Example:


```
CSV File

↓

DuckDB

↓

SQL Query

↓

Analysis Result

```



---

# 6.3 Machine Learning Support


Future:


```
Scikit-learn
```


Usage:


- Prediction
- Classification
- Clustering



V0:

Not required.



---

# 7. Database Technology


## 7.1 Main Database


Recommended:


```
PostgreSQL
```


Stores:


- Users
- Projects
- Dataset metadata
- Conversations
- Insights



Reason:


- Reliable
- Open source
- Strong ecosystem



---

# 7.2 ORM


Recommended:


```
SQLAlchemy
```


Responsibilities:


- Database models
- Query management
- Migration support



---

# 7.3 Migration Tool


Recommended:


```
Alembic
```


Used for:


- Database version control
- Schema migration



---

# 8. Storage Design


## 8.1 File Storage


V0 Development:


```
Local Storage
```


Stores:


- Uploaded CSV
- Excel files
- Generated reports



---

Production:


```
Object Storage
```


Examples:


- AWS S3
- MinIO



---

# 8.2 Vector Database


V0:


Not required.


Future:


Options:


```
pgvector

Chroma

Milvus
```


Used for:


- Semantic search
- Knowledge retrieval
- RAG



---

# 9. MCP Technology Direction


## V0


No complete MCP ecosystem.


Only reserve interfaces.


Example:


```
Data Connector

↓

Database

↓

Analysis System

```



---

## Future


MCP Runtime:


```
Agent

↓

MCP Client

↓

MCP Server

↓

External System

```


Support:


- Database MCP
- File MCP
- Business Tool MCP



---

# 10. Deployment Technology


# 10.1 Containerization


Recommended:


```
Docker
```


Purpose:


- Environment consistency
- Deployment simplicity
- Service isolation



---

# 10.2 Reverse Proxy


Recommended:


```
Nginx
```


Responsibilities:


- Request routing
- Static file serving
- HTTPS


---

# 10.3 Deployment Architecture


V0:


```
                Nginx

                  |

        ---------------------

        |                   |

        v                   v


Frontend Container   Backend Container


                            |

                            v


                    Database Container


```


---

# 11. Development Environment


## Frontend


```
Node.js

React

TypeScript

Vite
```



## Backend


```
Python 3.11+

FastAPI

SQLAlchemy
```



## Database


```
PostgreSQL
```



## AI Development


```
OpenAI Compatible SDK

Python AI Libraries
```



---

# 12. Recommended Project Structure


```
Nexa


├── frontend

│
│   ├── src

│   ├── components

│   ├── pages

│   └── services


├── backend

│
│   ├── api

│   ├── models

│   ├── services

│   ├── agents

│   ├── tools

│   ├── database

│   └── utils


├── storage


├── docs


└── docker-compose.yml

```


---

# 13. V0 Final Technology Stack


| Layer | Technology |
|----|----|
| Frontend | React + TypeScript |
| Build | Vite |
| UI | Ant Design |
| Data Tables | ag-grid-community |
| Visualization | ECharts |
| State | Zustand |
| Backend | FastAPI |
| Language | Python |
| Auth | JWT + bcrypt |
| Streaming | SSE (sse-starlette) |
| AI API | OpenAI Compatible API |
| Agent | Custom Agent Controller |
| Data Processing | Pandas |
| SQL Engine | DuckDB |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migration | Alembic |
| Storage | Local / Object Storage |
| Deployment | Docker + Nginx |


---

# 14. Future Evolution


## V1


Add:


- Better Agent Memory
- RAG
- LangGraph
- Advanced Data Understanding



---

## V2


Add:


- Skill System
- Skill SDK
- MCP Runtime
- Workflow Engine



---

## V3


Add:


- Multi-Agent Collaboration
- Marketplace
- Enterprise Platform
- Cloud Service



---

# 15. Technology Selection Principles


## Principle 1

Prefer simple solutions in V0.


## Principle 2

Avoid premature complexity.


## Principle 3

Every module should have a clear responsibility.


## Principle 4

Architecture should support future evolution.


## Principle 5

The product should be built around user value, not technology.


---

# End