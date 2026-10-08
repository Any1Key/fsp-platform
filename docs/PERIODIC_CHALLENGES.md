# Periodic employer challenges

Periodic challenges are a separate M11 evidence loop from one-off hiring-pipeline tasks. They are available only after an accepted reverse-recruitment match.

## Lifecycle

1. An employer creates a 5–20 minute challenge for one of its matched candidates and chooses a cadence from 1 to 90 days.
2. Cycle 1 is immediately available for the candidate and has a 72-hour response window.
3. The candidate submits one response for that cycle. The candidate sees only the prompt, their own response, and released results.
4. The employer grades against the immutable challenge rubric. A released result stores an `evidence_fresh_until` date equal to the configured cadence and schedules the next cycle at that date. The API derives `freshness.status` (`fresh`, `expiring`, or `stale`) and non-negative `freshness.days_remaining` from that date.
5. Each cycle remains in history. A challenge result is employer-specific evidence and never changes the platform assessment, verified grade, category, or ProofMatch score directly.

## API boundary

- `POST /api/v1/employer/challenges` — create a challenge for an owned `match_id`;
- `GET /api/v1/employer/challenges` — list owned cycles, submissions, rubric and results;
- `PUT /api/v1/employer/challenges/{assignment_id}/result` — grade a submitted cycle and optionally release it;
- `GET /api/v1/candidate/challenges` — list active cycles for the authenticated candidate;
- `POST /api/v1/candidate/challenges/{assignment_id}/submissions` — submit the authenticated candidate's current cycle.

The server enforces both role and match ownership. Scheduled cycles cannot be answered early; overdue cycles cannot be answered; and a cycle accepts only one submission. Rubric scores are validated server-side.

## Privacy and freshness

Challenge records contain no candidate contact, protected attributes, documents or tokens. Candidate result payloads omit rubric internals and employer drafts. `evidence_fresh_until` is an explicit lifecycle timestamp for the employer-specific result; it is not currently a global ranking input. Evidence is `expiring` when three or fewer days remain and `stale` after the timestamp passes. Freshness is an advisory renewal signal, not a grade or access gate.

Both challenge workspaces show the derived state so a candidate can see when a
short challenge should be renewed and an employer can see which employer-owned
evidence is still current.

Evidence: `backend/tests/test_periodic_challenges.py`.
