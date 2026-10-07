# Data model — target

## Identity/profile
- `user_identity`: id, keycloak_sub, email, one-time-bound platform role, timestamps.
- A verified Keycloak account without an application role is not persisted as a
  partial identity; it remains `pending` until candidate/employer onboarding
  completes. The selected role is then the local authorization binding and is
  checked against any explicit Keycloak role claim.
- `candidate_profile`: identity, protected contacts, private `date_of_birth`, summary, experience, role, preferences, privacy, consents, FSP link. Minor state is derived at read time from the private DOB and configured adult-age threshold; it is never a matching input. Processing and publication consent store policy version, timestamp and source; discoverability is separate and consent-dependent.
- `minor_consent_document`: candidate, policy version/status, original filename,
  content type/size/digest, UUID storage key, timestamps, and optional
  reviewer/audit metadata. File bytes are stored outside the database in a
  configured private directory and are never employer-visible.
- `company`: one employer-owned row per identity; name, description, industry,
  website, location, explicitly supplied public contact method, and timestamps.
  Trust fields remain future employer-discovery scope. The empty draft row is
  provisioned on the employer's first company-profile read, while a saved
  profile requires a non-blank name.

## Taxonomy
- `specialization`: active, stable slug/name for a professional track.
- `grade`: ordered `junior`/`middle`/`senior` vocabulary.
- `skill`: active, stable slug/name for evidence and hiring needs.
- `specialization_skill`: foreign-key mapping with an `is_core` flag; the
  composite key prevents duplicate mappings.
- assessment_blueprint

`GET /api/v1/taxonomy` is the read-only catalog boundary. It returns active
specializations with mapped skills, ordered grades, and explicit
`specialization-slug:grade-slug` category keys. A category is only an
employer-facing candidate category once the assessment boundary supplies a
verified grade; this catalog does not infer or store candidate results.

## Resume
- `resume_document`: candidate, safe original filename, PDF type/size/digest,
  UUID storage key, status (`uploaded`, `replaced`, `withdrawn`) and timestamps;
  bytes stay outside the database in private storage
- parsed_resume fields + confidence/provenance
- review status

## Platform assessment
- question_family
- question_template/version
- question_variant
- exposure/cooldown metadata
- attempt
- attempt_item
- answer
- rubric/result
- integrity_signal
- grade_decision
- retest_lock

Persist enough provenance to reproduce assembly and scoring.

## Evidence
`candidate_skill_evidence`:
- candidate
- skill
- source (`assessment`, `fsp`, `employer_task`, `challenge`, `resume`)
- scope (`global`, `employer_need`)
- raw/normalized score
- confidence
- measured_at
- stale_at
- provenance

## FSP
- `fsp_link`: candidate profile, provider, participant ID and link/update timestamps;
  one candidate-owned link is allowed.
- `fsp_achievement`: link-scoped external achievement ID, event/date/discipline,
  level/result, verification provenance and mapping version. The current synthetic
  adapter also snapshots canonical specialization/skill mapping and normalized
  result score/label; recency is derived from event date at read time so evidence
  can age without mutating the source snapshot. Later matching can consume this
  stable evidence graph.
- sync/provenance
- skill/relevance mapping version

## Employer need / matching
- hiring_need
- required/preferred skills
- specialization/grade target
- matching_snapshot
- matching_result
- score component version
- explanation components/confidence/gaps

Snapshot preserves result context during refinement.

## Invitations / match
- invitation
- salary min/max RUB
- offer description
- employer contact method
- status
- timestamps
- match/contact-unlock timestamp
- match relation

## Chat
- conversation (bound to match)
- conversation_member
- message
- message_read/read-state
- moderation/report record

No conversation exists or accepts messages before valid match.

## Vacancies/applications
- vacancy
- salary min/max RUB
- application
- application status history
- match event if accepted

## Employer hiring pipeline
- hiring_pipeline
- pipeline_stage (ordered/type/required)
- employer_task_template/version
- task_assignment
- task_submission
- employer_evaluation
- optional deterministic_check_result
- optional local_ai_draft metadata

Employer evaluation is employer-specific evidence by default.

## Local AI memory/jobs
- employer_task_example metadata/index reference
- ai_job (type/status/input reference/output reference, no secret token)
- employer_feedback on generated draft

## Challenges
- challenge
- assignment
- submission
- rubric/result
- evidence freshness effects

## Audit
- `audit_event`: actor identity, event type, non-PII JSON details and timestamp. Audit consent grants/withdrawals, discoverability changes and privacy export requests alongside future domain transitions.
- `privacy_request`: authenticated export/deletion request type and lifecycle status. The current MVP records export requests as `requested`; fulfillment and retention policy remain a later worker/legal-review concern.

Audit consent changes, minor-document events, contact/chat unlocks, grade decisions, invitation transitions, FSP link changes and employer grading events.
Never persist secret tokens in domain tables.
