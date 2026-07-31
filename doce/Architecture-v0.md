# Nexa V0 Architecture Design

Version: 1.0

Status: Planning

---

# 1. Overview

Nexa is an AI-powered data analysis workspace.

The V0 architecture focuses on enabling a complete data analysis workflow:

User Input

↓

AI Understanding

↓

Data Processing

↓

Analysis Execution

↓

Insight Generation

↓

User Presentation


The architecture is designed to support future evolution toward:

- Agent Runtime
- Skill Ecosystem
- MCP Ecosystem
- Workflow Automation

while keeping V0 simple and implementable.

---

# 2. High-Level Architecture


```
                    User

                     |

                     v

              Frontend Layer

                     |

                     v

          ┌─── Auth Gateway ───┐
          |   (JWT / API Key)  |
          └────────────────────┘

                     |

                     v

              Backend Service

                     |

        ----------------------------

        |             |            |

        v             v            v

 AI Analysis    Streaming     Data Layer

    Layer       Controller

        |             |

        v             v

 Agent Runtime    SSE Events
                  (progress
        |          updates)

        |

        v


 Analysis Tools

(Skills / MCP)


        |

        v


 Insight Generation


        |

        v


 Frontend Display

```


---

# 3. Core Architecture Layers


## 3.1 Frontend Layer


## Responsibility

Provide user interaction interface.


Main functions:

- Project management
- Data upload
- Chat interaction
- SQL editing
- Visualization display
- Insight viewing


Frontend does not handle:

- AI reasoning
- Data analysis logic
- Database operations


---

# 3.2 Backend Service Layer


## Responsibility

Provide application services and coordinate requests.


Main functions:

- User request handling
- Project management
- Data management
- Communication with AI layer
- Communication with data layer


Backend acts as the bridge between:

Frontend

AI System

Data System



## 3.2.1 Auth Gateway

## Responsibility

Authenticate every request before it reaches business logic.

Main functions:

- JWT token validation
- API route protection
- API Key encryption and proxying
- User session management

Key design decision:

The frontend never calls LLM providers directly. All AI requests go through the backend, which attaches the user's decrypted API key. This prevents key leakage, enables usage tracking, and allows future cost optimization (model selection, rate limiting).



## 3.2.2 Streaming Controller

## Responsibility

Manage SSE connections for real-time analysis progress.

Main functions:

- Establish SSE connection per analysis request
- Receive stage updates from AI Analysis Layer
- Push progress events to frontend
- Handle connection lifecycle (timeout, disconnect, error)

The Streaming Controller ensures the user never faces a "black box" loading state. Every stage of the analysis pipeline — from intent understanding to final insight — broadcasts its status as an SSE event.



---

# 3.3 AI Analysis Layer


## Responsibility

Understand user intent and generate analysis results.


Main components:


## Agent Runtime


Responsible for:

- Understanding user requests
- Maintaining conversation context
- Deciding analysis actions
- Calling analysis capabilities


V0 simplified:


User Request

↓

Intent Understanding

↓

Tool Selection

↓

Result Generation


---

## Analysis Skills


Built-in capabilities:


- SQL Generation
- Data Cleaning
- Statistical Analysis
- Visualization
- Report Generation


V0 uses internal skills.

Future:

Open Skill SDK.

---

# 3.4 Data Layer


## Responsibility

Manage user data and provide analysis access.


Supported sources:


V0:

- CSV
- Excel
- SQLite
- MySQL


Responsibilities:

- Data ingestion
- Schema understanding
- Query execution
- Result retrieval


---

# 3.5 Storage Layer


## Responsibility

Store application data.


Stores:


- User information
- Projects
- Dataset metadata
- Chat history
- Analysis results


---

# 4. Core Data Flow


## Data Upload Flow


```
User

↓

Frontend

↓

Backend

↓

Storage

↓

Dataset Metadata

↓

AI Understanding

```


---

## Analysis Flow


```
User Question

↓

Frontend Chat

↓

Backend API

↓

Agent Runtime

↓

Analysis Skill

↓

Data Source

↓

Analysis Result

↓

Insight Generation

↓

Frontend Display

```


---

## Auth Flow

```
User

↓

Frontend (stores JWT in localStorage)

↓

Backend Auth Middleware (validates JWT per request)

↓

Business Logic

↓

LLM Provider (via backend proxy + decrypted API Key)

```

The frontend never holds the raw API Key after initial setup. The key is encrypted at rest in PostgreSQL and decrypted only at the moment the backend proxies the request to the LLM provider.



## Streaming Flow

```
Frontend (opens SSE connection)

↓

Backend (validates JWT, initiates analysis)

↓

AI Analysis Layer (Agent Controller)

├── Stage 1: Intent Understanding → SSE event: "understanding"
├── Stage 2: Planning → SSE event: "planning"
├── Stage 3: SQL Generation → SSE event: "sql_generating"
├── Stage 4: Query Execution → SSE event: "querying"
├── Stage 5: Analysis → SSE event: "analyzing"
├── Stage 6: Visualization → SSE event: "visualizing"
└── Stage 7: Insight → SSE event: "insight" + final data

↓

Frontend renders progress bar and intermediate states
```



---

# 5. V0 Agent Architecture


V0 does not implement a complex multi-agent system.


Simplified architecture:


```
User Request

      |

      v

Agent Runtime

      |

      +------------+

      |            |

      v            v


SQL Skill    Visualization Skill


      |

      v


Data Source


      |

      v


Result


```


---

# 6. Future Architecture Evolution


The V0 architecture prepares for future expansion.


## Future:


```
                  Orchestrator

                       |

        --------------------------------

        |              |               |

        v              v               v


    Agent        Skill Runtime     MCP Runtime


                       |

                       v


              Resource Manager

                       |

                       v


              External World

```


Future capabilities:

- Multi-Agent
- Skill Marketplace
- MCP Marketplace
- Workflow Engine
- Data Intelligence Layer


---

# 7. Architecture Principles


## 1. Modular Design

Each capability should be independent.


---

## 2. AI as an Orchestrator

Users interact through goals instead of technical operations.


---

## 3. Progressive Evolution

V0 should support future architecture without unnecessary complexity.


---

## 4. Separation of Responsibility


Frontend:

User Experience


Backend:

Application Logic


AI Layer:

Reasoning and Decision


Data Layer:

Data Access


---

# 8. V0 Architecture Goal


The only goal of V0:


> Enable users to complete a data analysis task through natural language.


The architecture should prioritize:

- Simplicity
- Extensibility
- Clear boundaries

---

# End