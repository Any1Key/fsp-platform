# M15 secret/log and index/query audit

## Scope

Complete the two remaining M15 hardening items as one work unit:

- `NFR-006` — secure tokens, consent/privacy and server-side protection;
- `LEGAL-001` — 152-FZ-oriented minimization, RBAC and audit controls;
- supporting `NFR-004` — reproducible migration evidence;
- supporting `NFR-010` — stable query paths for the target load profile.

This plan does not change supervisor-owned `VERIFIED` or `READY` state.

## Evidence and findings

- The API has a generic exception boundary, but no shared log-redaction
  formatter/filter that protects future structured or diagnostic logs.
- The shell supervisor already redacts a small set of environment values, but
  the application and Python tooling need a tested, reusable boundary.
- The database is hand-written SQL over Alembic migrations. Existing indexes
  cover many foreign-key paths, but the audit identified missing leading-column
  coverage for discoverable candidate ordering, hiring-need skill access,
  candidate match access, employer invitation aggregates, conversation contact
  history and reviewer/trust queue ordering. Taxonomy specialization access
  is already covered by the composite primary key, and active privacy-request
  lookup is already covered by its partial unique index.

## Implementation steps

1. Add a Python safe-log formatter with redaction for bearer tokens, common
   secret assignments, password-bearing connection URLs, and exception text;
   install it at the API logging boundary without logging request bodies.
2. Add unit tests proving sensitive values are absent from formatted messages,
   including values supplied as logging arguments and exception text.
3. Add one forward-only Alembic migration for the missing composite indexes,
   with a migration test and an index contract test that names the audited SQL
   access paths.
4. Add a short security/query audit document describing the data excluded from
   logs, the query/index mapping, and the remaining deployment responsibility
   for PostgreSQL planner/load verification.
5. Mark only the two M15 backlog items and their requirement evidence as
   `IMPLEMENTED`; never mark `VERIFIED` or set `STATE.json` ready.

## Verification

- `backend/.venv/bin/pytest -q backend/tests/test_logging_safety.py backend/tests/test_query_indexes.py backend/tests/test_migrations.py`
- full backend test suite and Ruff checks;
- migration upgrade/downgrade and inspection of the new index names;
- repository status/diff review for secrets, unrelated files, and forbidden
  supervisor state changes.

## Result log

- 2026-10-11 16:15 MSK: selected as the single remaining M15 hardening unit
  under the deadline packing rules; implementation pending.
- 2026-10-11: implemented the safe Python logging boundary, migration
  `20261011_0030_security_query_audit`, focused regression tests and audit
  documentation. Added the supervisor `safe_tail` contract test and wired it
  into verification. Full backend verification passed: 192 tests.
