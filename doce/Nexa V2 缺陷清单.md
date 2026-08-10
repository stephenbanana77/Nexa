# Nexa Current Gap List

Date: 2026-08-10

This file replaces the old V2 gap list. Several earlier gaps are now partially or fully addressed, including backend tests, CI, Alembic, SQL safety, run lineage, search, export, and frontend build stability.

## Current Positioning

Nexa should be presented as:

> A trustworthy AI data analysis agent with SQL safety, run lineage, and offline evaluation.

The project should not be positioned as a full BI platform, enterprise collaboration suite, or ML workbench.

## Completed Baseline

- Backend test suite: 69 passing tests.
- Frontend lint and production build pass.
- GitHub Actions CI added.
- AST-based SQL policy added with `sqlglot`.
- Query timeout guard added for DuckDB and MySQL paths.
- Run lineage added to track question, schema snapshot, SQL attempts, policy decision, results, retries, and final answer.
- Run History frontend now displays evidence chain.
- Offline evaluation harness added with 12 Superstore golden cases.
- Frontend route and tab lazy loading added.

## Remaining Gaps

### P0: Evaluation Quality

- The current evaluation suite uses golden SQL as a deterministic baseline.
- It does not yet run the real Agent against every case and compare generated SQL/results.
- The suite should grow from 12 to 30-50 cases.
- Metrics should include:
  - SQL generation success rate
  - execution success rate
  - semantic accuracy
  - retry repair rate
  - p50/p95 latency
  - provider token cost

### P0: Real Token and Cost Tracking

- Token usage is still estimated.
- Provider usage metadata should be captured from the LLM response and written into lineage.
- Cost per successful analysis should be reported in evaluation.

### P1: SQL Policy Hardening

- SQL policy blocks unsafe operations and records risk flags.
- `SELECT *` and joins without conditions are flagged but not blocked.
- Future work:
  - dry-run / EXPLAIN validation
  - configurable risk gates
  - max selected columns
  - table allowlist
  - stricter connected database protections

### P1: Workflow Engine Maturity

- Workflow engine supports basic create/edit/run.
- It does not yet support branching, conditions, scheduling, durable resumability, or manual approval gates.

### P1: Demo and Deployment

- Needs a one-command demo seed path.
- Needs a hosted demo or recorded GIF.
- README now contains a demo path, but the setup still depends on local data and local services.

### P2: Notebook Python Safety

- Notebook Python execution needs sandboxing before being described as production-safe.
- Recommended direction: container sandbox or restricted execution environment.

### P2: Documentation Polish

- README and development guide are now current.
- Remaining docs should be reviewed before publishing the repository.

## Interview Talking Points

### How do you prevent dangerous SQL?

The Agent can generate SQL, but execution is gated by an AST policy using `sqlglot`. The policy allows only one read-only query expression, blocks DDL/DML nodes, strips comments, adds a top-level limit when missing, records risk flags, and writes the policy decision into lineage.

### How do you know an answer is reproducible?

Each run stores lineage: question, schema snapshot and hash, SQL attempts, policy decision, final SQL, result sample, retry/error information, and final answer. The frontend exposes this in Run History as an evidence chain.

### How do you know the Agent is improving?

Nexa has an offline evaluation harness with golden SQL cases. The next step is to run real Agent-generated SQL against the same cases and track semantic accuracy, retry repair rate, latency, and token cost over time.

### What is still not production-ready?

Notebook Python sandboxing, real provider token usage, larger evaluation set, hosted demo, and advanced workflow controls.
