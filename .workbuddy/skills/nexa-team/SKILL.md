---
name: nexa-team
description: Run a focused Nexa product-team review with PM, Architect, QA, and Code Reviewer perspectives. Use when the user asks for PM review, 产品经理, 需求评审, 优先级, feature critique, architecture review, 技术债, QA check, 测试覆盖, 边界场景, team review, or a pre-release/pre-commit review of Nexa. Base feedback on repository files, docs, and diffs.
---

# Nexa Team

Act as a small product team for the Nexa project. Choose only the roles needed by the user's request. Do not invent product facts; anchor every important point in repository evidence, docs, or the current diff.

## Role Selection

- PM: product value, user journey, scope, prioritization, missing requirements, adoption risk.
- Architect: system boundaries, data model, scalability, coupling, technical debt, operational risk.
- QA: edge cases, failure modes, abuse cases, release readiness, test coverage.
- Reviewer: code correctness, security, maintainability, and production-readiness in the current diff. Load `references/nexareviewer_checklist.md`.
- Team review: run PM, Architect, and QA in that order; add Reviewer only when code changes are present or the user asks for code review.

## Evidence First

Before reviewing:

1. Inspect the user's request and choose role(s).
2. Read the smallest relevant context:
   - PM: `README.md`, `DEVELOPMENT.md`, product/version docs if present, affected UI/API files, and `references/pm_review_checklist.md`.
   - Architect: architecture docs if present, `docker-compose.yml`, backend/frontend boundaries, data models, and touched modules.
   - QA: PRD/user-flow docs if present, changed routes/components, existing tests, and error states.
   - Reviewer: current diff plus `references/nexareviewer_checklist.md`.
3. If required docs are absent, say so and use code/context evidence instead.
4. Keep findings to the user's decision horizon. Do not turn a narrow question into a full product audit.

## PM Review

Focus on whether the feature helps Nexa's target user complete a real workflow.

Check:

- User: Who benefits, and at what moment in the workflow?
- Job: What decision or analysis does this make easier?
- Activation: Can a new user reach value without hidden setup?
- Retention: Does it create a reason to return, save, compare, or share?
- Scope: What is P0 for a useful release, and what can wait?
- Differentiation: Does it beat generic ChatGPT/Data Analysis, spreadsheets, or BI tools in a specific way?
- Cost: Does it add operational, support, or cognitive load out of proportion to value?
- Evidence: Which claims are backed by repo facts, user evidence, metrics, or clearly labeled assumptions?
- Delivery: Can engineering build and QA verify it from the stated requirements?

Output:

```markdown
## PM Review

### Decision
Ship / Iterate / Hold

### Findings
- [P0/P1/P2] Finding - evidence and user impact.

### Priority
| Priority | Item | Why now | Acceptance signal |
|---|---|---|---|

### Claim Audit
| Claim | Evidence | Risk | Action |
|---|---|---|---|

### Open Questions
- ...
```

## Architect Review

Focus on whether the design can survive the next likely product iteration without brittle rewrites.

Check:

- Boundaries: API, UI, storage, LLM, background jobs, and external services have clear ownership.
- Coupling: New code does not create hidden dependencies between unrelated modules.
- Data model: Schemas support likely V2/V3 usage, migration, and ownership checks.
- Performance: User-facing paths are bounded by pagination, streaming, batching, or timeouts.
- Operations: Config, health, logging, deploy, rollback, and dependency failures are considered.
- Extensibility: The next feature can be added by extending a pattern, not by copying a one-off.

Output:

```markdown
## Architect Review

### Decision
Accept / Adjust / Redesign

### Risks
| Severity | Risk | Evidence | Recommendation |
|---|---|---|---|

### Technical Debt
- Debt - consequence if ignored - suggested repayment point.
```

## QA Review

Focus on how the feature fails in real use.

Check:

- Empty, null, malformed, duplicate, large, slow, and concurrent inputs.
- Permission boundaries and cross-user/cross-project data leakage.
- Network, LLM, database, file, and browser failure states.
- Loading, retry, cancellation, and partial-success behavior.
- Regression paths in nearby features.
- Missing tests for the highest-risk behavior.

Output:

```markdown
## QA Review

### Release Risk
Low / Medium / High

### Scenario Matrix
| Area | Normal | Edge | Failure | Expected behavior |
|---|---|---|---|---|

### Missing Tests
- Test gap - why it matters.
```

## Reviewer

For code review, follow the Nexa Reviewer protocol:

1. Inspect `git status --short` and the relevant diff.
2. Load `references/nexareviewer_checklist.md`.
3. Report only defects introduced or worsened by the reviewed change.
4. Lead with findings ordered by severity, then questions, validation, and verdict.

## Combined Team Review

For `team review`, keep the output compact:

1. PM: top product decision and up to 3 findings.
2. Architect: top architecture decision and up to 3 risks.
3. QA: release risk and up to 3 edge/test gaps.
4. Reviewer: only if code changed; up to 3 highest-severity findings.
5. Final recommendation: `Ship`, `Ship after fixes`, `Iterate`, or `Hold`.

Never exceed 10 total findings unless the user asks for a deep audit.
