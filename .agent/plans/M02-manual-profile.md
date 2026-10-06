# M02 manual candidate profile

## Purpose / user value

Give an authenticated candidate a private, editable professional profile that can be
reviewed before later assessment, resume, and discovery steps. The profile is self-scoped
and stores structured experience without exposing protected identity/contact data through
the profile API.

## Requirement IDs

- `CAND-001` — Candidate profile manual form.
- `CAND-012` — Candidate cannot access others' private data (server-side self scope).
- `CAND-014` — Private/protected candidate attributes remain outside matching inputs.
- Product journey: `consent/privacy → profile/resume`.

## Current behavior

Authentication and candidate privacy endpoints lazily create a `candidate_profile`, but
there is no profile read/update API, profile-specific validation, or candidate profile UI.
The existing table provides `summary`, JSON `experience`, and JSON `preferences` storage.

## Proposed design

- Add `GET /api/v1/candidate/profile` and `PATCH /api/v1/candidate/profile`.
- Resolve the profile only from the authenticated candidate's identity; reject employer
  access through the existing role dependency.
- Store a display name, headline, location, summary, structured experience entries,
  skills, and work preferences. Keep email/contact data out of the response; identity
  email remains an authentication attribute, not a public profile field.
- Validate bounded lengths, calendar-month dates, and structured entry shape with
  Pydantic. Do not use DOB, age, or other protected traits.
- Add a responsive profile editor to the signed-in candidate panel with loading, save,
  validation/error, and success states.

## Files/modules

- `backend/app/candidates.py` — candidate profile application service and validation shape.
- `backend/app/main.py` — request/response models and routes.
- `backend/tests/test_candidate_profile.py` — API, validation, persistence, and RBAC tests.
- `frontend/src/components/candidate-profile.tsx` — profile editor.
- `frontend/src/components/auth-status.tsx` — render candidate profile in candidate context.
- `frontend/src/app/globals.css` — branded responsive profile styles.
- `docs/API_GUIDELINES.md` / `docs/PRODUCT_SPEC.md` — document the implemented slice.
- `.agent/BACKLOG.md` / `docs/REQUIREMENTS_MATRIX.md` — mark only this work unit `IMPLEMENTED`.

## Data/API changes

Add a migration for `candidate_profile.display_name`, `headline`, and `location`; reuse
the existing JSON columns for structured experience and preferences. PATCH merges the
provided candidate-owned fields atomically and returns the canonical profile plus
`updated_at`.

## Security/privacy implications

The API is candidate-role-only and always resolves identity by the verified token subject.
No employer route is added. DOB, minor state, contacts, resume contents, consent details,
and assessment results are not accepted or returned by this endpoint. Audit logs do not
contain submitted profile text.

## Test plan

- Candidate can read the initially empty profile and save/re-read a valid profile.
- Invalid experience shape/length is rejected without partial persistence.
- Employer token receives `ROLE_REQUIRED` for both profile methods.
- A second candidate cannot read or mutate the first candidate's profile.
- Backend full test suite, Ruff, and frontend typecheck/build pass.

## Demo/evidence

The signed-in candidate view contains the profile editor, displays saved values after
reload, and stays usable on narrow screens. Evidence path is the implementation/test
files; external supervisor owns verification.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished unit in M02.
- 2026-10-07: kept specialization/grade and protected DOB/minor state out of this slice
  because they are separate backlog items with their own taxonomy/privacy workflows.
- 2026-10-07: implemented the self-scoped API, migration, responsive editor, and
  authorization/validation tests. Status is `IMPLEMENTED`; external supervisor owns
  verification.
