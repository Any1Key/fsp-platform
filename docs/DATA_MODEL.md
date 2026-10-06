# Data model — target

## Identity/profile
- `user_identity`: id, keycloak_sub, email, one-time-bound platform role, timestamps.
- A verified Keycloak account without an application role is not persisted as a
  partial identity; it remains `pending` until candidate/employer onboarding
  completes. The selected role is then the local authorization binding and is
  checked against any explicit Keycloak role claim.
- `candidate_profile`: identity, protected contacts, summary, experience, role, preferences, privacy, consents, FSP link, private DOB/minor state.
- `minor_consent_document`: candidate, version/status, protected file metadata, timestamps, reviewer/audit metadata.
- `company`: owner, name, description, industry, public contacts, trust fields.

## Taxonomy
- specialization
- grade
- skill
- specialization_skill
- assessment_blueprint

## Resume
- resume_document metadata
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
- fsp_link
- fsp_achievement
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
Audit consent changes, minor-document events, contact/chat unlocks, grade decisions, invitation transitions, FSP link changes and employer grading events.
Never persist secret tokens in domain tables.
