# Nexa V0 Information Architecture

Version: 1.0

Status: Planning

---

# 1. Overview

Nexa V0 is an AI-powered data analysis workspace.

The information architecture defines the structure of user-facing pages and how users navigate through the product.

The core user journey:

```
Home

↓

Create Project

↓

Import Data

↓

Ask Question

↓

Generate Analysis

↓

Save Insight
```

---

# 2. Overall Application Structure


```
Nexa

├── Home
│
├── Project Workspace
│
│   ├── Overview
│   │
│   ├── Data
│   │
│   ├── Chat
│   │
│   ├── SQL
│   │
│   ├── Notebook
│   │
│   └── Insights
│
└── Settings

```

---

# 3. Home Page

## Purpose

Provide the entry point for users.

Help users quickly start a new data analysis project.


---

## Main Components


## Recent Projects

Display:

- Project name
- Last update time
- Dataset information


Example:

```
Sales Analysis

Updated 2 hours ago
```


---

## Create Project

Main action:


```
+ New Project
```


Creates a new analysis workspace.


---

## V0 Not Included

- Marketplace
- Community
- Templates
- Team workspace


---

# 4. Project Workspace

## Purpose

The core working environment of Nexa.

Each project represents an independent analysis task.


Example:

```
Sales Analysis Project
```


A project contains:

- Dataset
- Conversations
- SQL queries
- Notebooks
- Analysis results


---

# 5. Project Overview Page


## Purpose

Provide a quick understanding of the current project.


---

## Components


### Dataset Summary

Display:

- Dataset name
- Row count
- Column count
- Data source
- Creation time


Example:

```
Dataset:

sales.csv


Rows:

120,000


Columns:

15
```


---

### Recent Insights

Display previous analysis results.


Example:


```
Sales dropped 15% in July
```


---

# 6. Data Page


## Purpose

Manage and understand project data.


---

## Features


## Dataset List


Display all connected datasets.


Example:


```
sales.csv

users.xlsx

orders.db
```


---

## Dataset Detail


Show:


- Schema
- Column names
- Data types
- Missing values
- Sample records


Example:


| Column | Type |
|---|---|
| date | datetime |
| sales | number |
| region | string |


---

## Data Preview


Provide a table view similar to spreadsheet.


Users can:

- Browse data
- Check structure


---

# 7. Chat Page


## Purpose

The primary interaction interface.

Users communicate with data through natural language.


---

## Layout


```
--------------------------------

Chat History | Conversation | Context

--------------------------------
```


---

## User Interaction Example


User:

```
Why did sales decrease last month?
```


Nexa:


```
I analyzed:

1. Sales trend

2. Regional performance

3. Product performance


Main finding:

East region sales decreased 20%.
```


---

## Core Capability

Chat should support:

- Asking questions
- Follow-up questions
- Context understanding
- Analysis explanation



---

## Streaming Progress Indicator

While AI analyzes data, the Chat page shows a streaming progress bar with current stage and description:

```
┌─────────────────────────────────────────────────────┐
│  🔄 Analyzing your data...                           │
│  ┌──────────────────────────────────────────────┐    │
│  │████████████████░░░░░░░░░░░░░░░░░░░░░ 45%     │    │
│  └──────────────────────────────────────────────┘    │
│  Executing SQL query on 120,000 rows...              │
└─────────────────────────────────────────────────────┘
```

Each stage updates both the progress percentage and the description text. Completed stages are shown as checkmarks in the chat history, giving the user a transparent view of what the AI is doing.

### Progress Stages:

| Icon | Stage | Description |
|------|-------|-------------|
| 🧠 | Understanding | "Understanding your question..." |
| 📋 | Planning | "Planning analysis steps..." |
| ⚡ | SQL Generating | "Generating SQL query..." |
| 🔍 | Querying | "Executing query on N rows..." |
| 📊 | Analyzing | "Analyzing query results..." |
| 📈 | Visualizing | "Generating charts..." |
| 💡 | Insight | "Generating final insight..." |
| ✅ | Done | Analysis complete |



---

## Chat → Notebook Transition

When a Chat response contains SQL or Python code, the user sees an "Open in Notebook" button:

```
┌───────────────────────────────────────────────┐
│ Nexa: Sales decreased 15% in East region.     │
│                                               │
│ 📊 [Bar Chart: Regional Sales]                │
│                                               │
│ Generated SQL:                                │
│ SELECT region, SUM(sales) FROM...             │
│                                               │
│ [📓 Open in Notebook]  [💾 Save Insight]      │
└───────────────────────────────────────────────┘
```

Clicking "Open in Notebook" navigates to the Notebook page, auto-populated with the generated SQL and Python code from this analysis, allowing advanced users to refine AI output manually.


---

# 8. SQL Page


## Purpose

Provide SQL capabilities for advanced users.


---

## Features


## SQL Editor


Support:

- Write SQL
- Edit SQL
- Execute SQL


---

## AI SQL Generation


Example:


User:

```
Find top 10 products by revenue
```


Nexa:


```sql
SELECT ...
```


---

## Query Result


Display:

- Result table
- Execution status


---

# 9. Notebook Page


## Purpose

Provide an advanced analysis environment.


---

## Supported Cells


### Markdown Cell

For documentation.


### SQL Cell

For database queries.


### Python Cell

For advanced analysis.


---

## Example Flow


```
Markdown

↓

SQL

↓

Python Visualization

```


---

# 10. Insights Page


## Purpose

Store and manage analysis results.


---

## Insight Card


Each insight contains:


```
Question:

Why did sales decrease?


Analysis:

Sales dropped 15%


Charts:

3


Created:

Today
```


---

## Future Extension

Insights can evolve into:


- Insight Library
- Knowledge Base
- Reports


---

# 11. Settings Page


## Purpose

Manage user preferences.


---

## V0 Features


Include:


- Model API Key
- Account Settings
- Basic Preferences


---

# 12. Navigation Structure


Recommended layout:


```
Nexa

├── Home
│
├── Projects
│
│   └── Current Project
│
│       ├── Overview
│       ├── Data
│       ├── Chat
│       ├── SQL
│       ├── Notebook
│       └── Insights
│
└── Settings

```


---

# 13. Page Priority


## P0 (Must Have)


### Chat

Core AI interaction.


### Data

Data import and understanding.


### Insights

Output and value delivery.


---

## P1 (Important)


### SQL

Support technical users.


### Notebook

Support advanced analysis.


---

## P2 (Future)


### Dashboard

AI-generated dashboards.


### Workflow

Automated analysis pipelines.


### Collaboration

Team features.


---

# 14. V0 Golden Path


The most important user journey:


```
Open Nexa

↓

Create Project

↓

Upload CSV

↓

AI Understands Data

↓

Ask Question

↓

Generate Analysis

↓

View Insight

↓

Save Result

```


---

# Design Principle


## 1. Goal-oriented

Users describe goals, not technical operations.


## 2. AI-first

Natural language is the primary interface.


## 3. Progressive Disclosure

Simple users see simple workflows.

Advanced users can access SQL and Notebook.


## 4. Every Analysis Creates Value

Questions and results should become reusable assets.


---

# End