# FSP registry integration concept

No real FSP API/schema is available for the hackathon. Do not hard-wire an invented production external schema.

## Port

```text
FspRegistryPort
  get_participant(fsp_id)
  list_achievements(fsp_id)
  verify_link(...)
```

Implementations:
- `SyntheticFspRegistryAdapter` for demo/tests;
- future Keycloak/HTTP adapter.

The current implementation is in `backend/app/fsp.py`. It exposes candidate-owned
endpoints:

- `GET /api/v1/candidate/fsp` — returns `not_linked` or `linked`, the history state,
  and safe achievement fields;
- `POST /api/v1/candidate/fsp-link` — verifies and snapshots a synthetic participant
  after processing consent, using a replaceable `FspRegistryPort`;
- `DELETE /api/v1/candidate/fsp-link` — removes the candidate-owned link and snapshot.

The deterministic demo IDs are `FSP-DEMO-001` (two synthetic achievements) and
`FSP-DEMO-NONE` (a valid participant with no history). Unknown IDs are rejected.
These fixtures are demo data and are labelled as synthetic in the candidate UI.

## Synthetic canonical achievement

Use replaceable internal fields such as:
- achievement id;
- participant reference;
- event name;
- event date;
- discipline/category label;
- level/importance label;
- achievement type (participation/finalist/prize/win/etc. as synthetic data);
- placement/result when applicable;
- verification/provenance;
- optional mapping to canonical skills with mapping version.

Do not present synthetic labels as the real future FSP API contract.

## Evidence mapping

When an achievement is linked, the synthetic adapter snapshot is normalized to
the platform taxonomy without changing the source fields:

- a known discipline maps to a canonical specialization and skill slugs;
- achievement type and numeric placement become an explainable `result_score`
  from 0 to 100 and a `result_label`;
- `recency_score` and `recency_label` are derived from the event date when the
  response is read, so a record can age without rewriting the source snapshot;
- an unknown discipline remains unmapped and is still retained/displayed.

The mapping is deterministic and versioned. It is evidence normalization, not a
ranking decision: no employer need, protected attribute, or candidate exclusion
is involved here.

## Ranking contribution

`backend/app/fsp.py` now provides the reusable `calculate_fsp_contribution` service
and its persistence-backed `calculate_fsp_contribution_for_candidate` loader. The
future ProofMatch service supplies a `FspRankingNeed` containing canonical
specialization, required skills and preferred skills.

For each relevant achievement, the service calculates:

- relevance from specialization match or required/preferred canonical skill overlap;
- result strength (40% of evidence strength);
- event level (20%);
- recency (20%);
- non-empty registry verification provenance (20%).

The three strongest relevant achievements are aggregated with diminishing weights of
70%, 20% and 10%, then multiplied by the configured FSP ranking weight (10 points by
default). The final contribution is always capped at that weight. The result includes
the ranking version, score components, matching skills, contributing achievement IDs
and human-readable reasons so employer UI can show the exact evidence later.

Missing FSP history returns `score: 0` with `history_status: no_history`; unrelated
history also returns zero. Neither state is a penalty or an eligibility exclusion.
The service is intentionally internal until the M06 employer-discovery endpoint
consumes it; candidate FSP HTTP responses continue to expose the evidence snapshot.

## Linking / Keycloak demo

Keep application auth identity and FSP participant link separate. Demonstrate linking a synthetic FSP ID to the authenticated candidate and show how a future Keycloak/FSP identity federation could replace the synthetic adapter.

## No-history path

Candidate with no FSP ID or no achievements remains fully searchable/rankable through platform assessment and other evidence.

The current M05 slice stores/displays normalized evidence and calculates the bounded
contribution contract. M06 will consume the same snapshot in employer discovery and
render the contribution alongside the rest of the ProofMatch explanation.
