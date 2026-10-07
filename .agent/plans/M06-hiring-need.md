# M06 hiring need — ExecPlan

## Scope

Implement the first unfinished M06 work unit: an employer can describe one
current hiring need with team, role, specialization, target grade, and
taxonomy-backed required/preferred skills. This is the input boundary for
later Talent Radar and ProofMatch work; it does not rank candidates, create
invitations, or publish a vacancy.

## Requirement IDs and evidence

- `EMP-002`: employer hiring need contains team/stack/specialization/grade.
- `DOC-003` (supporting documentation): matching/category model records
  specialization/grade targets and required/preferred skills as structured
  matching input.

## Implementation steps

1. Add normalized `hiring_need` and `hiring_need_skill` tables owned by the
   employer company, with a uniqueness boundary for the current need.
2. Add employer-scoped GET/POST/PATCH API routes. Validate specialization,
   grade, active skills, specialization-to-skill mapping, duplicate skills,
   and required/preferred overlap on the server.
3. Add API tests for persistence, partial update, taxonomy validation,
   duplicate protection, ownership, and role authorization.
4. Add the employer responsive hiring-need editor using the public taxonomy
   catalog, including loading, empty, error, saved, and disabled states.
5. Update API/data-model/work-unit documentation and mark only the directly
   evidenced requirement as `IMPLEMENTED` in the requirements matrix and
   backlog. Leave `VERIFIED` and readiness decisions to the external
   supervisor.

## Validation

- `pytest -q` in `backend`.
- `npm run typecheck` and `npm run build` in `frontend`.
- Review migration and API error-envelope behavior.

## Implementation result

Implemented with migration `20261007_0012`, employer API/UI, automated
ownership and validation coverage, and supporting API/data-model documentation.
The work unit is marked `IMPLEMENTED` only; external supervisor verification
and readiness remain out of scope.
