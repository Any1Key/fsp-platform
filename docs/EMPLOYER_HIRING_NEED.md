# Employer hiring need

`EMP-002` is implemented as the first structured input boundary for M06.
An employer can save one current hiring need scoped to its company. The need
contains a team, role, target specialization, target grade, and at least one
taxonomy skill split into `required_skills` and `preferred_skills`.

## API

- `GET /api/v1/employer/hiring-need` returns the employer's need or `null`.
- `POST /api/v1/employer/hiring-need` creates the current need.
- `PATCH /api/v1/employer/hiring-need` partially updates it.

The server derives the company from the authenticated Keycloak subject. It
validates active specialization and grade slugs, active skill slugs, duplicate
skills, and required/preferred overlap. Skills are catalog-backed but are not
restricted to the specialization's core mapping: a real hiring stack can
include adjacent platform skills. A failed update is validated before the
existing need is changed.

The API returns skill labels alongside stable slugs so the employer UI does
not need to duplicate taxonomy names. This slice deliberately stops before
candidate ranking, Talent Radar aggregation, snapshots, invitations, and
vacancies; those remain separate M06/M07/M11 work units.

The responsive employer workspace loads the public taxonomy and renders an
empty editor when no need exists, then switches to update mode after the first
successful save. Loading, failure, success, and disabled-save states are
explicitly represented.
