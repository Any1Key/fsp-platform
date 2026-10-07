# M06 employer company profile

## Purpose / user value

Give an authenticated employer a durable company identity that can be shown in
the reverse-recruitment journey before hiring needs and invitations are added.

## Requirement IDs

- `EMP-001` — employer company profile.

## Current behavior

Employer Keycloak role onboarding and `/api/v1/employer/context` exist, but no
company record, employer-owned API, or employer-facing profile editor exists.

## Proposed design

Add one company row per employer identity. The self-scoped API lazily provisions
an empty profile on `GET` and updates only the authenticated employer's row on
`PATCH`. Store only company-facing fields: name, description, industry,
website, location, and a public contact method. Do not expose Keycloak email or
candidate/private data through this boundary.

## Files/modules

- `backend/alembic/versions/20261007_0011_company_profile.py`
- `backend/app/companies.py`
- `backend/app/main.py`
- `backend/tests/test_company_profile.py`
- `frontend/src/components/employer-company-profile.tsx`
- `frontend/src/components/auth-status.tsx`
- `frontend/src/app/globals.css`
- `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`, `docs/EMPLOYER_COMPANY_PROFILE.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/STATUS.md`

## Data/API changes

- `company` table with unique `owner_identity_id`, a nullable name for the
  initial empty draft, optional company description/industry/website/location/
  public contact, and timestamps. The API requires `name` before saving.
- `GET /api/v1/employer/company` returns the current employer's profile.
- `PATCH /api/v1/employer/company` validates and saves a complete field patch.

## Security/privacy implications

Both routes require the employer role and derive ownership from the validated
Keycloak subject. The response contains no account email, tokens, private
candidate data, or protected attributes. Website validation accepts only
`http`/`https` URLs; public contact is explicitly employer-entered text.

## Test plan

- migration reaches head on the existing SQLite test harness;
- employer can read/save/reload its profile;
- validation rejects blank/overlong/unsafe values without partial updates;
- candidate cannot access the employer boundary;
- two employers cannot read each other's data.

## Demo/evidence

The employer role view mounts a responsive company profile form with loading,
error, empty and saved states. API contract and UI path are documented for the
next hiring-need slice.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished M06 unit because the backlog is
  ordered and `EMP-001` is the first employer-discovery prerequisite.
- 2026-10-07: no registration/company verification workflow is invented here;
  trust fields and public discovery remain later scope.
