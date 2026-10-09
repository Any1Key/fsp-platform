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
