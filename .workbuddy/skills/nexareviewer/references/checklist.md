# Nexa Review Checklist

Use this checklist to find concrete defects in the reviewed diff. Mark an area `n/a` when the change does not touch that surface.

## 1. Auth and Authorization

- New FastAPI routes require `current_user: User = Depends(get_current_user)` unless the route is explicitly public.
- Data access must be scoped to the current user, tenant, project, or workspace where applicable.
- Admin-only or destructive operations must check role/permission, not just authentication.
- Frontend route guards must not be the only access control.

Common failure: a new endpoint accepts an `id` and fetches by primary key without verifying ownership.

## 2. Input Validation and Injection

- Request bodies should use Pydantic models or typed schemas, not raw `dict`, unless at a boundary with explicit validation.
- User-controlled SQL must not be string-concatenated. Use ORM parameters or vetted query builders.
- User input inserted into LLM prompts should pass through the project's prompt/input sanitization utility when one exists.
- File uploads must validate type, size, extension, and parse failures.
- Shell commands must avoid user-controlled string interpolation.

Common failure: accepting a user prompt, table name, filename, or SQL snippet and passing it directly to an LLM, SQL engine, filesystem path, or shell.

## 3. Error Handling

- Do not swallow exceptions with `pass`, empty returns, or generic success states.
- Log unexpected exceptions with enough context, but never log secrets, tokens, raw credentials, or sensitive user data.
- Convert internal failures to appropriate API errors with stable response shapes.
- Streaming/SSE/generator endpoints must handle errors inside the generator and close resources.
- Frontend async flows should surface a useful error state and not leave permanent loading spinners.

## 4. Type Safety and Contracts

- TypeScript should avoid `any`; use narrow types, discriminated unions, or typed boundary adapters.
- Python public functions and FastAPI handlers should have useful parameter and return types.
- API request/response models should match frontend assumptions.
- Optional/null fields must be handled explicitly on both backend and frontend.
- Renames must update imports, exports, route references, tests, and docs/examples.

## 5. Data Access, Pagination, and Performance

- New list endpoints must paginate or otherwise bound result size.
- Avoid unbounded `.all()`, full file reads, full table scans, and N+1 queries on user-facing paths.
- Expensive LLM, database, or file operations should have timeouts and cancellation/error paths.
- Derived data should be cached or memoized only when invalidation is clear.
- Large frontend lists should avoid avoidable rerenders or blocking work in render.

## 6. Config, Secrets, and Environment

- No hardcoded secrets, tokens, API keys, model keys, or private URLs.
- Environment-dependent values should come from settings/config with documented defaults.
- Timeouts, limits, model names, base URLs, and feature flags should not be magic literals in product code when they affect operations.
- `.env.example`, deployment config, and startup code should stay consistent when new config is required.

## 7. Concurrency and State

- Shared mutable state must be protected or made immutable.
- Async code must not run long blocking calls directly in the event loop.
- Background tasks need failure logging and lifecycle ownership.
- Temporary files, caches, and registries must be safe under concurrent requests.
- Retries must be bounded and avoid duplicating side effects.

## 8. Resource Cleanup

- Files, DB sessions, network clients, and temporary directories must be closed or cleaned up.
- Long-running streams should handle client disconnects.
- Upload, preview, export, and analysis flows should delete temp artifacts on both success and failure.

## 9. Observability

- Critical paths should emit logs for start/failure/important state transitions.
- Logs should include stable identifiers such as user id, job id, dataset id, or request id where useful.
- Health checks should reflect new required dependencies if the change adds one.
- Metrics/tracing are not required for every change, but missing visibility on async or external-service flows is a review concern.

## 10. Tests and Release Safety

- New behavior should have targeted tests at the level that catches the likely failure: unit, integration, API, or UI.
- Bug fixes should include a regression test when practical.
- Schema or config changes need migration/backward-compatibility consideration.
- The change should not require manual setup that is missing from docs or examples.
- If tests are absent, call out the highest-risk untested path instead of demanding generic coverage.

## Verdict Guide

- `Ready to push`: no P0/P1 findings, no unresolved key checklist failures, and relevant validation passed or was reasonably skipped.
- `Not ready`: any P0/P1 finding, broken validation, or an unresolved auth/data/security/config issue.
- `Risk accepted`: only when the user explicitly accepts a known risk.
