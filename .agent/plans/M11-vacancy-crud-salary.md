# M11 vacancy CRUD and mandatory salary

## Purpose / user value

Give an employer a durable, company-scoped vacancy draft that can be edited,
published, and closed while enforcing the product rule that every vacancy has a
positive RUB salary range. This is the first M11 slice; candidate browsing and
applications remain separate work units.

## Requirement IDs

- `DATA-001` — salary min/max RUB is mandatory in a vacancy.
- `EMP-010` — this slice covers the publish/edit vacancy half only; incoming
  applications remain TODO until the candidate application unit is complete.

## Current behavior

The repository has employer company and hiring-need boundaries, but no vacancy
table, API, or employer UI. The M11 backlog starts with vacancy CRUD and salary.

## Proposed design

- Add an employer-owned `vacancy` table with draft/published/closed lifecycle.
- Add `/api/v1/employer/vacancies` list/create routes and an item read/update
  route. Publishing is an explicit action; `DELETE` is a reversible close.
- Keep all reads and writes company-scoped through the authenticated Keycloak
  identity. Published vacancies are stored for the following candidate browse
  unit; this slice does not expose them publicly yet.
- Validate `0 < salary_min_rub <= salary_max_rub` in both request and domain
  service layers. Return the stable API error `VACANCY_SALARY_INVALID`.
- Add an employer workspace panel with loading, empty, error, save, publish,
  and closed states.

## Files/modules

- `backend/alembic/versions/20261008_0022_vacancies.py`
- `backend/app/vacancies.py`
- `backend/app/main.py`, `backend/app/errors.py`
- `backend/tests/test_vacancies.py`, `backend/tests/test_migrations.py`
- `frontend/src/components/employer-vacancies.tsx`
- `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/EMPLOYER_VACANCIES.md`, `docs/DATA_MODEL.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`

## Data/API changes

- `vacancy`: company FK, title, description, optional location/work mode/
  employment type, mandatory salary range, lifecycle timestamps, and optional
  taxonomy specialization/grade references.
- `GET/POST /api/v1/employer/vacancies`
- `GET/PATCH/DELETE /api/v1/employer/vacancies/{vacancy_id}`
- `POST /api/v1/employer/vacancies/{vacancy_id}/publish`

## Security/privacy implications

Vacancies are private to the owning employer in this slice. Candidate contact
data is never involved. `DELETE` closes rather than physically deletes a row so
future application/history references remain recoverable.

## Test plan

- migration creates the vacancy table and expected foreign keys;
- salary positivity and min/max ordering are enforced without partial writes;
- create/read/update/publish/close persist lifecycle state;
- another employer cannot read or mutate the row and candidates receive the
  normal role boundary;
- frontend typecheck/build remains green.

## Demo/evidence

The employer workspace shows a vacancy editor and status badge after login.
`backend/tests/test_vacancies.py` is the primary integration evidence for the
company boundary and mandatory salary rule.

## Progress / decisions / surprises

- 2026-10-08: selected as the first unfinished M11 work unit. Candidate browse,
  applications, accepted-application matching, and periodic challenges are
  explicitly out of scope.
- 2026-10-08: implemented migration, company-scoped API lifecycle, employer
  panel, docs, and integration evidence. `DATA-001` is `IMPLEMENTED`; `EMP-010`
  remains `TODO` pending incoming-application behavior. External supervisor
  owns verification and readiness.
- 2026-10-08: focused vacancy/migration tests pass (`4 passed`), the full
  backend suite passes (`111 passed`), Ruff passes, and frontend typecheck /
  production build pass.
