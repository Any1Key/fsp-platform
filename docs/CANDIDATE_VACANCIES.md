# Candidate vacancies and applications

The first candidate-facing M11 slice provides a separate, salary-bearing path from vacancy discovery to application status tracking.

## Candidate API

- `GET /api/v1/candidate/vacancies` returns only `published` vacancies. It includes title, description, salary, location/work mode/employment type, optional specialization and grade, and the safe company name. Employer contact details, candidate contact details, protected attributes and documents are never included. Each row also reports the authenticated candidate's own application state, if one exists.
- `POST /api/v1/candidate/vacancies/{vacancy_id}/applications` creates one application with initial status `submitted`. Processing consent is required. The vacancy must still be published; a duplicate candidate/vacancy pair returns `APPLICATION_EXISTS`.
- `GET /api/v1/candidate/applications` returns only the authenticated candidate's applications, including the vacancy summary, current status and append-only status history.

Application statuses are `submitted`, `reviewing`, `shortlisted`, `rejected`, and `withdrawn`. This slice creates only `submitted`; employer-side review and status transitions are a later M11 unit.

An application does not create a match, unlock contacts, or enable chat. The later accepted-application work unit will use the existing server-side match/contact boundary described in `docs/CHAT_AND_MATCHING.md`.

## Privacy and lifecycle

Vacancy discovery is role-protected but does not require candidate publication consent because it reads public employer offers. Persisting an application requires processing consent. Closing a vacancy is a soft lifecycle transition; existing applications remain readable in the candidate's history while the closed vacancy disappears from the open browse list.

The database enforces a unique `(vacancy_id, candidate_profile_id)` pair and stores the initial status in `application_status_history`. Candidate responses are scoped by the authenticated candidate profile, so another candidate cannot read or affect an application.

## UI states

The candidate workspace renders `VACANCY RADAR` with published offers and mandatory salary, an explicit apply action, an already-applied disabled state, a processing-consent explanation, empty/loading/error states, and `STATUS TRACKER` history. No direct contact action is rendered before a match.
