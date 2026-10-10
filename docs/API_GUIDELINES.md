# API guidelines

Base: `/api/v1`.

Use:
- resource-oriented URLs;
- typed Pydantic schemas;
- consistent pagination;
- stable error envelope with request ID;
- RFC3339 timestamps UTC;
- UUID identifiers;
- explicit state-transition endpoints for domain actions when CRUD would hide invariants.

Error shape target:
```json
{
  "error": {
    "code": "CONTACT_LOCKED",
    "message": "Candidate contact data is not available before unlock.",
    "request_id": "..."
  }
}
```

The implementation returns this envelope for HTTP errors, request validation
errors, unknown routes and unexpected server failures. Every response includes
the same value in `X-Request-ID`; callers may provide a safe identifier in that
header, otherwise the API generates a UUID. Public error codes are stable
identifiers such as `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`,
`ASSESSMENT_ATTEMPT_NOT_FOUND` and `DATABASE_UNAVAILABLE`; implementation
exception text is never returned.

Document 400/401/403/404/409/422 cases where relevant.
Do not leak protected resource existence across authorization boundaries.

## ATS integration contract

`GET /api/v1/integrations/ats/v1/contract` is a public, data-free discovery
endpoint for the versioned vendor-neutral ATS contract. It returns the typed
`fsp.ats.event.v1` envelope, supported vacancy/invitation/application/match
events, HMAC webhook headers, the five-minute replay window, idempotency rule,
retry statuses, and the contact-unlock policy. It does not return credentials,
candidate data, or a vendor-specific configuration.

Future inbound webhooks must be verified by an employer-scoped connector using
the raw request bytes, `X-FSP-Signature`, and `Idempotency-Key`. The connector
must make duplicate deliveries side-effect free. The existing invitation and
match state machine remains authoritative: an ATS event cannot unlock contact
before an accepted invitation creates a match. See `docs/ATS_INTEGRATION.md`.

## Taxonomy catalog

`GET /api/v1/taxonomy` returns active non-sensitive specialization, grade, and
skill metadata for onboarding and future employer filters. It also returns
explicit category keys formed as `specialization-slug:grade-slug`. The route
is read-only and does not expose candidate profile data or assessment results;
the assessment service remains responsible for deciding whether a candidate's
declared grade is verified.

## Validation dashboard

Authenticated employers, reviewers, and admins may call `GET
/api/v1/validation/dashboard` to read the deterministic, aggregate synthetic
validation projection used by the demo UI. The response includes source
versions, dataset counts/seed, macro matching ranking metrics, assessment
metrics, grade confusion counts, and item-family discrimination values.

Candidates receive `403 ROLE_REQUIRED`; unauthenticated callers receive the
usual authorization error. The endpoint is read-only and never returns
candidate identities, PII, raw relevance labels, assessment answer keys, or
submission content. Values are calibration evidence, not a production hiring
decision. See `docs/VALIDATION_DASHBOARD.md`.

## Employer hiring need

The employer-only `GET`, `POST`, and `PATCH /api/v1/employer/hiring-need`
routes store the current company-owned hiring context for later Talent Radar
and ProofMatch work. The payload contains `team`, `role`, `specialization`,
`grade`, `required_skills`, and `preferred_skills`. Skills are returned with
their labels and slugs. A need must contain at least one skill, cannot repeat
a skill across preference groups, and cannot use inactive or unknown taxonomy
values. Ownership is derived from the validated principal; candidates and
other employers cannot read or mutate the record.

## Candidate privacy

`GET /api/v1/candidate/privacy` returns only the authenticated candidate's
processing consent, publication consent, policy version/timestamps and
discoverability state. `PATCH` accepts one or more boolean state changes; the
server supplies the configured policy version and records a non-PII audit
event. Publication requires processing consent, and discoverability requires
publication consent. A minor also requires a current submitted/approved
representative consent document before publication; the server withdraws
publication and discoverability if an existing profile becomes minor without
one. Withdrawing processing consent cascades to dependent settings.

`POST /api/v1/candidate/privacy/export` records an authenticated export
request and returns `202` with a request ID and `requested` status. It is an
MVP request concept; fulfillment is intentionally delegated to a future
privacy worker and legal-reviewed retention policy.

## Candidate profile

`GET /api/v1/candidate/profile` returns only the authenticated candidate's
professional self-description. `PATCH` saves the editable display name,
headline, location, summary, structured experience, skills, and work
preferences after processing consent is granted. The profile endpoint never
returns identity email, contacts, DOB/minor state, resume documents, consent
metadata, or assessment results. Employers receive `ROLE_REQUIRED` and cannot
use this self-scoped resource.

## Employer company profile

`GET /api/v1/employer/company` and `PATCH /api/v1/employer/company` are
employer-only and derive the company owner from the validated Keycloak subject.
The first read provisions an empty company profile for a stable UI empty state;
the first save requires `name`. The patch accepts `name`, `description`,
`industry`, `website`, `location`, and explicitly supplied
`public_contact_method`. Website values must use `http` or `https`.

The response contains company-facing fields only. It does not expose the
employer account email, tokens, candidate data, or protected attributes. A
candidate receives `ROLE_REQUIRED`; invalid input uses `VALIDATION_ERROR`,
`COMPANY_NAME_REQUIRED`, or `COMPANY_PROFILE_UPDATE_REQUIRED` as applicable.

## Employer trust / anti-fraud

`GET /api/v1/employer/trust` is employer-only and returns a derived trust
projection. The `verified_email` badge is based only on the verified Keycloak
claim. Domain, website consistency, profile completeness, account age,
invitation outcomes, duplicate offers, and offer-language checks are returned
as explicitly labeled `heuristic` signals. The response also shows the
employer's rolling 24-hour invitation usage and current limit.

`POST /api/v1/candidate/invitations/{invitation_id}/report` is candidate-only.
It accepts `fake_vacancy`, `fee_request`, `misleading_offer`, `spam`, or
`other`, with optional details. The server verifies that the invitation is
addressed to the authenticated candidate and makes repeated reports from that
candidate idempotent. Report details are not copied into audit metadata.

`GET /api/v1/reviewer/trust/reports` and `PATCH
/api/v1/reviewer/trust/reports/{report_id}` are restricted to `reviewer` and
`admin` roles. Open reports form the review queue; a report can be marked
`reviewed` or `closed`. An open report or at least two independent high-risk
heuristics lowers the outbound invitation limit from 20 to 3 per 24 hours.
One heuristic alone never blocks or rejects an invitation, and trust does not
participate in candidate ranking or protected-attribute processing.

## Candidate vacancies and applications

The candidate-only `GET /api/v1/candidate/vacancies` route returns published
salary-bearing vacancies and the authenticated candidate's own application
state. `POST /api/v1/candidate/vacancies/{vacancy_id}/applications` requires
processing consent, accepts only a currently published vacancy, and creates a
single `submitted` application. A duplicate returns `APPLICATION_EXISTS`; a
draft or closed vacancy returns `VACANCY_NOT_PUBLISHED`.

`GET /api/v1/candidate/applications` returns only the authenticated candidate's
applications, with the safe vacancy summary, current status and append-only
status history. These routes never expose employer contact details or
protected candidate fields. An application alone does not create a match or
unlock chat; that transition remains behind the accepted-application boundary.

## Employer hiring pipeline

Employer-only `GET` and `PUT /api/v1/employer/hiring-pipeline` configure the
ordered stages attached to the current hiring need. A pipeline contains two to
twelve stages. `platform_review` and `final_decision` are required boundary
stages; employer stages can be inserted, removed and reordered. Each stage has
an employer-facing `title`, `required` flag and estimated duration from 5 to
480 minutes. The server derives ownership through the authenticated employer's
company and rejects invalid boundary/order payloads without partially writing
the replacement.

Salary-bearing invitation responses include `pipeline_stages`, a safe snapshot
of only stage type/title/required/duration captured when the invitation is
created. This lets a candidate understand the expected process before
accepting; task content, answers and contacts are not included.

### Employer task authoring

Employer-only task routes are scoped to the current employer's hiring need:

- `GET /api/v1/employer/tasks` lists task definitions and version metadata;
- `POST /api/v1/employer/tasks` creates version 1 as a draft and requires an
  `employer_task` pipeline stage;
- `PATCH /api/v1/employer/tasks/{task_id}/draft` edits the current draft, or
  starts the next draft version when the current version is published;
- `POST /api/v1/employer/tasks/{task_id}/versions` creates a complete next
  draft when no draft exists;
- `POST /api/v1/employer/tasks/{task_id}/publish` explicitly publishes the
  draft and retires the prior published version.

Task content contains instructions, active taxonomy skill slugs, expected
grade, time/deadline policy, and rubric dimensions/points. Published versions
are immutable. Ownership is checked through the authenticated employer's
company and hiring need; candidate and other-employer requests receive no task
content. The authoring routes do not assign tasks or grade submissions;
candidate assignment is covered by the match-bound routes below.

`POST /api/v1/employer/tasks/draft-suggestion` is the optional local-AI
boundary. It returns the adapter status plus `approved_example_count` and a
bounded `approved_examples` metadata list. Examples are selected only from
published task versions owned by the current employer and ranked against the
current hiring need. With local AI disabled, `draft` remains `null`; with the
opt-in adapter enabled, `draft` contains a server-validated task/rubric proposal
and advisory `difficulty_rationale`. The proposal is never persisted or
published by this route. Transport, timeout, malformed JSON and constraint
failures return an explicit `failed` status; manual authoring continues.

### Candidate employer-task assignments

After an invitation is accepted and a `talent_match` exists, published
employer tasks are assigned to the matched candidate. The assignment stores
the exact published task version, pipeline stage and server-derived deadline.
The candidate-only routes are:

- `GET /api/v1/candidate/task-assignments` lists assignments for the
  authenticated candidate's matches. It reconciles newly published tasks for
  existing matches, but never exposes tasks before match.
- `POST /api/v1/candidate/task-assignments/{assignment_id}/submissions` stores
  a numbered text submission revision and returns the refreshed assignment.

The response includes stage title, task title/instructions/target skills,
expected grade, estimated duration, deadline and the candidate's own
submission history. It excludes the employer rubric, contacts, identity
subjects and other candidates. A released employer evaluation adds only score,
feedback and release time. Submissions after the deadline return
`TASK_ASSIGNMENT_DEADLINE_PASSED`; assignment ownership failures return
`TASK_ASSIGNMENT_NOT_FOUND`.

### Employer task evaluation

Employer-only `GET /api/v1/employer/task-assignments` lists submissions for
matches owned by the authenticated employer's company. `PUT
/api/v1/employer/task-assignments/{assignment_id}/evaluation` accepts one score
for each dimension of the assigned immutable rubric, derives the 0–100 score,
and saves employer-specific evidence. The candidate must have submitted at
least one response. `release_to_candidate: false` keeps the evaluation as a
draft; `true` releases only the derived score and feedback to the candidate.
Other employers and candidates receive a safe not-found/role response, and
the endpoint does not update platform assessment results.

## Internal chat

The `/api/v1/chat/conversations` endpoints are available only to candidate and
employer identities. They require conversation membership established by an
accepted invitation/match; no endpoint accepts a match ID as a substitute for the
membership check. Unauthorized conversation IDs use the same not-found response to
avoid cross-user existence leaks. Message bodies are persisted for authorized
history but are excluded from audit/log metadata. Read receipts are per identity,
and contact exchange is a match-scoped user action.

## Employer Talent Radar

`GET /api/v1/employer/talent-radar` is employer-only and requires the current
company hiring need. It returns a read-only ProofMatch snapshot with category
aggregates, ranked candidate cards, score components, evidence edges, reasons,
confidence/freshness, gaps, and the bounded FSP contribution. Optional filters
are `q`, `specialization`, `grade`, `skill`, `fsp` (`all`, `with_history`, or
`without_history`), `include_unconfirmed`, and `limit`.

Each candidate also includes `fit_band` (`ready_now`, `strong_fit`,
`potential_fit`, or `explore`) as a human-readable explanation band derived
from the existing score and grade state. An unconfirmed candidate is always
`potential_fit`; the field is advisory presentation data and never an
automatic hiring or rejection decision.

## Periodic challenge freshness

`GET /api/v1/candidate/challenges` and `GET /api/v1/employer/challenges` keep
their existing role and match/company scope. A released challenge `result`
contains `evidence_fresh_until` plus a server-derived `freshness` object:

```json
{
  "status": "fresh",
  "days_remaining": 12,
  "evidence_fresh_until": "2026-10-20T12:00:00Z"
}
```

The status is `expiring` when three or fewer days remain and `stale` after the
timestamp passes. Candidate responses continue to omit rubric scores. This
employer-specific freshness state is advisory and never mutates the platform
grade, ProofMatch score, match, or chat permissions.

The candidate projection includes only profiles with publication and
discoverability consent. It exposes professional display fields only; email,
OIDC subjects, date of birth/minor state, resumes, FSP participant IDs, and
contacts are excluded. `include_unconfirmed=false` is an explicit verified-only
view; unconfirmed and unassessed candidates are otherwise retained with a
visible grade-state marker. Missing FSP history contributes zero and does not
exclude a candidate. The snapshot carries candidate IDs plus scoring, evidence,
and need-version identifiers so a later filter can be audited against the
same selection.

## Candidate dashboard

`GET /api/v1/candidate/dashboard` returns the authenticated candidate's safe
assessment overview. Ownership is derived from the verified principal subject;
the route accepts no candidate ID. The response includes profile display
fields, the latest submitted category/grade result, retest availability and
recent-first attempt history. `current_assessment` is `null` until an attempt
is submitted. An unconfirmed result remains visible with its declared grade,
`verified_grade: null` and `grade_state: not_confirmed`.

The route does not return answer keys, prompts, integrity telemetry, email,
contacts, protected DOB/minor state or consent metadata. Employers receive
`ROLE_REQUIRED`. See `docs/CANDIDATE_DASHBOARD.md` for the bootstrap storage
boundary and UI states.

## Candidate Verified Skill Passport

`GET /api/v1/candidate/skill-passport` is a candidate-only, read-time
projection of the authenticated candidate's evidence. It combines the latest
system-scored platform assessment, mapped FSP achievement snapshots, and
candidate-entered profile skills while returning source, status, confidence,
provenance, measured time, and freshness for each evidence card. It also
returns explicit `not_started`, `unconfirmed`, and `no_history` states.

The route accepts no candidate ID and does not return contacts, email, DOB or
minor-document data, answer keys, assessment prompts, or integrity telemetry.
Platform assessment freshness is a display signal (fresh through 365 days,
aging through 730 days, then stale); it never changes eligibility or grade.
FSP history remains additive and missing history contributes no penalty.

## Candidate assessment attempts

The base assessment routes require a candidate role. `POST
/api/v1/assessments/attempts` accepts only `specialization` and
`declared_grade`; the server derives ownership from the verified Keycloak
subject. Supplying `candidate_id` is rejected as a validation error. The
corresponding `GET` and `POST .../submit` routes return
`ASSESSMENT_ATTEMPT_NOT_FOUND` for an unknown or another candidate's attempt,
so attempt existence is not disclosed across ownership boundaries.

The create response includes prompts, options, session artifacts, and item
metadata, but never answer keys or correct options. Submission returns the
system score, grade state, and advisory integrity signals. A submitted attempt
may also contain `integrity_evidence` for a cross-submission similarity review:
it is limited to the signal code, `text`/`code` modality, the candidate's own
progressive item scope and a rounded score. Comparator identity, comparator
content and raw submitted text are never returned. The client sends only
disclosed minimal telemetry; integrity signals cannot automatically reject a
candidate or change the deterministic grade. The candidate UI uses the public
taxonomy catalog to render specialization and grade choices and disables
specializations without an administered blueprint.

Submitted attempts also include `canonical_review`. Its `delayed` form has
only `status` and `available_at`; it never includes `correct_option` or
canonical explanation. The `available` form adds those details only after all
family/version windows have closed or the families have been explicitly
retired. The default window is 90 days from first family/version exposure and
is configured with `CANONICAL_EXPOSURE_WINDOW_DAYS`. In-progress attempts do
not include review data.

## Candidate resume upload

`GET /api/v1/candidate/resume` returns the authenticated candidate's latest
private resume metadata or `document: null`. `POST /api/v1/candidate/resume`
accepts one multipart `resume` part. Processing consent is required. The
server validates the `.pdf` filename, `application/pdf` MIME type, `%PDF-`
signature, and configured size limit before writing the bytes under a UUID
storage key with private permissions. A successful replacement marks the
previous current document `replaced` and returns `201` with safe metadata only:
ID, display filename, type, size, status and upload time. Storage keys, hashes,
file bytes and parsed resume text are never returned. Parser extraction and
candidate review are a subsequent workflow.

## Protected candidate identity data

`GET /api/v1/candidate/protected-profile` and
`PATCH /api/v1/candidate/protected-profile` are candidate-only endpoints for
the private date of birth. The response derives `minor_state` on the server as
`not_set`, `minor`, or `adult` using the configured adult-age threshold. The
client cannot submit an age or state. Writes require processing consent, and a
future date is rejected. The endpoint is separate from the professional
profile and never exposes the value to employers or matching code. The
parent/legal-representative document is handled by the separate protected
workflow below.

## Minor consent document

`GET /api/v1/candidate/minor-consent-document` returns only the authenticated
candidate's derived minor state, requirement flag, policy version and safe
metadata for the latest document. `POST` accepts one multipart `document` PDF,
validates its type/signature and configured size limit, and returns `201` with
metadata/status only. The PDF bytes stay under the configured private storage
directory and are never returned by the API. Upload requires processing consent
and a server-derived minor state; a replacement marks the previous record
`replaced` while retaining protected storage for retention handling. Employers
receive `ROLE_REQUIRED` for both routes.
