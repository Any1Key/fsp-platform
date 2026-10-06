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
