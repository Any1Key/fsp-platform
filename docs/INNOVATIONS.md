# Verified Skill Passport

The candidate workspace exposes a read-time Verified Skill Passport at:

```text
GET /api/v1/candidate/skill-passport
```

The endpoint is candidate-role protected and has no candidate-ID parameter, so
it can only project the authenticated candidate's own evidence. It returns the
current category and grade state, a bounded freshness summary, FSP link/history
state, and evidence cards with:

- source: `platform_assessment`, `fsp`, or `profile`;
- status: `verified`, `unconfirmed`, or `declared`;
- mapped skills, score where applicable, confidence, measured date, freshness,
  provenance, and a human-readable detail;
- no DOB, minor-consent document, contact data, answer keys, or integrity
  telemetry.

## Evidence rules

Platform assessment evidence is generated only from the system-scored base
assessment. A passing result is `verified`; a failed declared-grade assessment
remains `unconfirmed` and never rewrites the declared grade. The current
assessment specialization maps to the active taxonomy skills for the passport
view.

FSP achievements are read from the persisted adapter snapshot and retain the
existing result and recency mapping. FSP is additive evidence: `no_history` is
an explicit normal state and does not remove the candidate from discovery.

Profile-entered skills are shown as `declared` with lower confidence and no
freshness date. They are context, not platform verification.

For the passport display, platform assessment evidence is fresh for 365 days,
aging through 730 days, and then stale. FSP uses the existing achievement
recency bands (`recent`, `aging`, `old`, `stale`, or `future`). Freshness never
deletes evidence and is not a ranking gate.

The UI places the passport before the detailed FSP link-management panel so a
candidate can understand the evidence graph even when no FSP identity is
linked.

## Blind Discovery

Employer Talent Radar supports an evidence-first privacy mode through
`GET /api/v1/employer/talent-radar?blind=true`. Candidate identity fields are
masked by the backend while category, grade state, ProofMatch score, evidence,
confidence, freshness, reasons, and gaps remain available. The employer can
still send a salary-bearing invitation using `blind_discovery: true`; the
candidate decides whether to accept before the employer receives the identity
in a matched invitation view.

Blind mode is a presentation and invitation privacy boundary, not a ranking
change. It uses the same explainable score and does not use protected traits.
Blind query matching excludes name, headline, and location so search cannot
undo the masking. The mode does not expose contacts, DOB, documents, email, or
assessment answer data.

## Career Graph

The candidate workspace exposes a self-scoped, read-time Career Graph at:

```text
GET /api/v1/candidate/career-graph
```

It composes the latest submitted platform assessment, active taxonomy, mapped
FSP achievements, and profile declarations into an evidence map. The response
contains:

- the current specialization and declared/verified grade state;
- skill nodes with `verified`, `unconfirmed`, or `declared` status, source,
  confidence, evidence count, and freshness;
- the current category, the next grade when the current grade is verified, and
  the highest-overlap adjacent taxonomy paths;
- matched skills, explicit evidence gaps, and a small summary for the UI.

Path suggestions are navigation aids, not hiring guarantees or automatic grade
decisions. A declared or unconfirmed skill may be shown as context but never
becomes verified through graph projection. Candidates without FSP history still
receive the graph from their platform/profile evidence, and a candidate with no
assessment receives an explicit starting state and assessment next step.

The endpoint accepts no candidate ID and omits contacts, DOB/minor state,
documents, answer keys, integrity telemetry, and protected traits. It performs
no writes and does not use age, location, or identity fields to form paths.
