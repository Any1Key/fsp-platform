# M15 security and query audit

Audit date: 2026-10-11. This is an engineering control record for `NFR-006`
and `LEGAL-001`, not a legal certification.

## Secret and log boundary

The API installs `backend/app/logging_safety.py` at startup. `SafeLogFilter`
redacts bearer credentials, access/refresh/ID tokens, common API/client/bot/
database/Keycloak/Telegram/OpenAI keys, passwords and secrets, password-bearing
database URLs, and sensitive query values (`q`, contact fields and credential
parameters). It also sanitizes logging arguments, exception tracebacks and
stack text before a handler formats them.

The API does not log request bodies. Access-sensitive state is represented by
request IDs and safe status metadata. The supervisor shell boundary separately
redacts configured database, identity-provider, Telegram, API and repository
token variables when it writes diagnostic tails. Tokens,
passwords, raw resume/minor-document bytes, full chat bodies, contact values
and unnecessary protected attributes remain excluded from audit details.

Regression coverage is in `backend/tests/test_logging_safety.py` and
`agent/test-secret-log-contract.sh`. It verifies
direct messages, format arguments, URLs, search parameters and exception text;
the test uses synthetic values only.

## Query/index audit

The hand-written SQL paths were compared with the indexes materialized by the
Alembic head migration. Migration `20261011_0030` adds the following leading
column coverage:

| Query path | Index | Purpose |
| --- | --- | --- |
| Talent Radar candidate eligibility/order | `ix_candidate_profile_discoverable_updated` | Narrow discoverable candidates before the ordered scan |
| Hiring-need skill replacement/read | `ix_hiring_need_skill_need_preference` | Candidate need lookup and preference grouping |
| Candidate match/task discovery | `ix_match_candidate` | Resolve matches by candidate profile |
| Pending employer invitation duplicate check | `ix_invitation_employer_candidate_status` | Scope the three-column duplicate predicate |
| Employer trust invitation statistics | `ix_invitation_company_created` | Restrict the rolling company window |
| Matched conversation contacts | `ix_conversation_contact_conversation_created` | Conversation-scoped chronological contact reads |
| Reviewer trust queue | `ix_employer_trust_report_status_created` | Status-scoped chronological queue reads |

Existing primary, unique and composite indexes cover the remaining audited
foreign-key and authorization lookups, including candidate/application,
invitation inbox, message history, task assignment, privacy-request and
minor-document paths. The index test checks exact table/column definitions;
PostgreSQL planner and authenticated target-load measurements remain deployment
verification responsibilities.

## Operational boundary

The application uses parameterized SQL and a bounded connection pool. A
multi-worker deployment still needs a trusted ingress/shared rate-limit store,
PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` review against representative data, and
production log-sink retention/access controls. Those checks are not claimed by
this implementation unit.
