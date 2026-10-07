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

Convert achievements to a bounded `fsp_evidence_score` using:
- relevance to the employer need/skills;
- result strength;
- event level;
- recency;
- verification confidence.

Keep the score explainable and capped. Missing FSP history = zero bonus, never a penalty or exclusion.

Employer UI should show the exact achievement reasons contributing to the score.

## Linking / Keycloak demo

Keep application auth identity and FSP participant link separate. Demonstrate linking a synthetic FSP ID to the authenticated candidate and show how a future Keycloak/FSP identity federation could replace the synthetic adapter.

## No-history path

Candidate with no FSP ID or no achievements remains fully searchable/rankable through platform assessment and other evidence.

The current M05 slice stores/displays the normalized evidence but does not
calculate a ranking score. Matching will consume this snapshot through the same
port and add the separately tested, bounded positive contribution in the
employer-discovery slice.
