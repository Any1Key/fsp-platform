# M05 bounded FSP ranking contribution

## Purpose / user value

Turn the normalized synthetic FSP achievement snapshot into a transparent positive
signal that a later employer ProofMatch query can consume. A candidate with no FSP
history remains eligible and receives zero bonus; FSP evidence can never exclude a
candidate or exceed its configured ranking weight.

## Requirement IDs

- `FSP-003` — synthetic achievements contribute a bounded positive ranking signal.
- `CORE-003` / `MATCH-002` — the contribution is evidence for the future verified-profile
  ranking boundary, without implementing employer discovery in this work unit.

## Current behavior

FSP links and normalized achievements are persisted and displayed to the candidate.
The repository has no reusable ranking contribution calculation; the FSP integration
document explicitly defers scoring until matching consumes the snapshot.

## Proposed design

- Add a pure, deterministic contribution calculator in `backend/app/fsp.py`.
- Match an achievement to a need by canonical specialization and required/preferred
  skill overlap.
- Weight relevant achievement strength by result, event level, recency, and non-empty
  verification provenance.
- Aggregate at most the three strongest relevant achievements with fixed diminishing
  weights and cap the result at the configured 10-point FSP component.
- Add a persistence-backed loader keyed by candidate profile ID so M06 can consume the
  same candidate-owned snapshot without copying ranking logic.
- Return score components, contributing achievement IDs, matched skills, and reasons
  for explainable downstream cards.

## Files/modules

- `backend/app/fsp.py`
- `backend/tests/test_fsp.py`
- `docs/FSP_INTEGRATION.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Data/API changes

No migration or public HTTP endpoint is added. The internal service consumes existing
`fsp_achievement` snapshots and returns a typed contribution contract for the M06
matching service. Candidate FSP HTTP responses remain unchanged.

## Security/privacy implications

The calculator reads only canonical achievement evidence already consent-gated and
owned by the candidate profile. It has no access to DOB, contacts, chat, or protected
attributes. No-FSP and unrelated-FSP states return zero rather than a penalty.

## Test plan

- no history and no relevant achievements return zero;
- relevant achievements produce a positive explainable contribution;
- contribution is capped at 10 points even with many perfect achievements;
- freshness, result, level, verification, specialization, and skill relevance affect
  the deterministic score;
- the persistence loader reads the existing FSP snapshot and preserves no-history;
- existing FSP linking/scoping tests remain green.

## Demo/evidence

Unit and SQLite integration tests in `backend/tests/test_fsp.py` are the evidence for
the bounded contribution contract. Employer-facing rendering and full ProofMatch
ranking remain the separate M06 work unit.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished item in M05.
- 2026-10-07: kept employer discovery out of scope because M06 owns the matching
  endpoint/UI; the service is intentionally ready for that consumer.
