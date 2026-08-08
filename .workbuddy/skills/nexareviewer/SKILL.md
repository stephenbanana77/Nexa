---
name: nexareviewer
description: Review Nexa project code changes before commit or push. Use when the user asks for review, code review, 审查, 检查代码, 提交前检查, or wants to know whether the current git diff is safe. Review only changed files and report concrete bugs, security risks, missing tests, and production-readiness issues with file/line evidence.
---

# Nexa Code Reviewer

Perform a read-only review of the current change set. Do not edit files, stage changes, commit, or push while using this skill.

## Scope

1. Inspect `git status --short`.
2. Determine the diff to review:
   - Prefer staged changes: `git diff --cached`.
   - If nothing is staged, review unstaged tracked changes: `git diff`.
   - For a specific commit/range requested by the user, review that range instead.
3. Review only changed `.py`, `.ts`, `.tsx`, `.js`, `.json`, `.yml`, and `.yaml` files.
4. Skip generated or vendored paths: `dist/`, `build/`, `node_modules/`, `.venv/`, `venv/`, coverage outputs, and lockfiles unless the user asks.
5. Treat deleted files as in scope only for behavioral impact: imports, routes, scripts, docs, or references that may now break.

## Required Context

Before judging the diff, read only the smallest useful project context:

- `README.md` and `DEVELOPMENT.md` when the change affects product behavior, setup, API shape, or deployment.
- Nearby code for each changed file, not the whole repository.
- Existing tests or fixtures covering the touched module when available.
- `references/checklist.md` for Nexa-specific production standards.

## Review Method

Use the checklist as a guide, not a box-ticking form. A finding must satisfy all three conditions:

1. It is introduced or made worse by the reviewed change.
2. It has a concrete failure mode, security risk, data risk, or maintainability cost.
3. It can be tied to a file and line or a clearly named changed block.

Avoid speculative findings. If something is uncertain, label it as a question or residual risk rather than a defect.

## Severity

- P0: Data loss, auth bypass, secret exposure, remote code execution, broken deploy, or app-wide outage.
- P1: User-visible broken behavior, security weakness, broken API contract, missing migration, major performance regression.
- P2: Edge-case bug, missing important test, brittle error handling, observability gap.
- P3: Style, naming, small cleanup, or local consistency issue. Include only when it materially helps.

## Output

Lead with findings, ordered by severity. Keep the report short and evidence-driven.

```markdown
## Review Report

### Findings
- [P1] path/to/file.py:42 - The changed handler returns all rows without pagination. A large workspace can load the full table and time out; use `offset(skip).limit(limit)` and return `{items, total, skip, limit}`.

### Open Questions
- Does this endpoint intentionally allow anonymous access?

### Checklist Summary
| Area | Result | Notes |
|---|---|---|
| Auth | pass/fail/n/a | ... |
| Error handling | pass/fail/n/a | ... |
| Tests | pass/fail/n/a | ... |

### Verdict
Ready to push / Not ready
```

If there are no findings, say so clearly, then mention tests not run or residual risk.

## Validation

Run targeted validation only when it is cheap and relevant:

- `pytest path/to/test_file.py` for backend Python changes.
- `npm test`, `npm run lint`, or `npm run typecheck` for frontend changes when scripts exist.
- Do not run broad, slow commands unless the user asked for exhaustive validation.

Report every command attempted and whether it passed, failed, or was skipped.
