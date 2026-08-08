# Nexa PM Review Checklist

Use this checklist for PM review, PRD critique, roadmap critique, feature shaping, and requirement clarification. The goal is to turn vague product thinking into evidence-backed, buildable, testable decisions.

## 1. Problem Framing

- Name the user segment, not just "users".
- State the job-to-be-done or workflow moment.
- Separate the user problem from the proposed solution.
- Identify the pain frequency, severity, and current workaround.
- Flag solution smuggling: a feature request that hides an unvalidated problem.

## 2. Evidence and Claim Audit

For each important claim, classify evidence:

- `file`: backed by repository docs, code, analytics exports, specs, or tickets.
- `user`: backed by interviews, support tickets, sales calls, or direct customer examples.
- `metric`: backed by measured funnel, retention, usage, revenue, latency, or quality data.
- `assumption`: plausible but unverified.
- `unknown`: no evidence visible.

High-risk claims are claims that drive roadmap, pricing, migration, launch, or engineering scope without evidence. Do not present assumptions as facts.

## 3. Outcome and Metrics

- Define the outcome before the feature list.
- Prefer user or business outcomes over shipping outputs.
- Include one primary success metric and 2-4 guardrail metrics when possible.
- Define metric numerator, denominator, time window, and segment.
- Avoid vanity metrics unless tied to a decision.

Useful metric patterns for Nexa:

- Activation: first successful upload, first useful analysis, time to first insight.
- Retention: repeat analysis, saved/report exports, returning workspace usage.
- Quality: analysis accepted, corrected, regenerated, or abandoned.
- Reliability: analysis failure rate, preview failure rate, LLM timeout rate.

## 4. Scope and Prioritization

Classify requirements:

- P0: Without this, the feature does not solve the core problem or creates unacceptable risk.
- P1: Important for adoption or quality, but not required for first useful release.
- P2: Nice-to-have, polish, or later optimization.

Watch for scope smells:

- Multiple unrelated personas in one feature.
- Admin, analytics, collaboration, and automation all bundled into v1.
- Requirements that cannot be tested.
- "Flexible/customizable" with no concrete first use case.

## 5. User Stories and Acceptance Criteria

Use this format when requirements need to become engineering work:

```markdown
As a [specific user/persona],
I want to [do a concrete action],
so that [measurable or observable outcome].
```

Acceptance criteria should use Given/When/Then and include normal, edge, and failure cases:

```markdown
Given [context],
When [user action],
Then [observable result].
```

Avoid acceptance criteria that only check element existence. They should describe user outcomes and system behavior.

## 6. Launch Readiness

- State the target user and excluded users.
- Define the minimum lovable path and fallback path.
- Note migration, permission, data, pricing, support, and docs impact.
- Define what would make the launch a rollback or pause.
- List decisions that need human confirmation before engineering starts.

## PM Verdict Guide

- `Ship`: problem, user, scope, and acceptance criteria are clear enough to build and test.
- `Iterate`: direction is promising, but scope, metrics, evidence, or acceptance criteria need tightening.
- `Hold`: problem framing is weak, evidence is missing for a high-impact claim, or the feature is mostly solution-first.
