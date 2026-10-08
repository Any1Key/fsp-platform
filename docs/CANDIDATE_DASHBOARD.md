# Candidate dashboard

The candidate dashboard is the self-scoped assessment overview at:

`GET /api/v1/candidate/dashboard`

It requires a candidate role and derives ownership from the authenticated
Keycloak subject. The client cannot provide another candidate ID. The response
contains only:

- profile display name and headline;
- the latest submitted assessment as `current_assessment`;
- the declared grade, optional verified grade, score and explicit
  `verified`/`not_confirmed` state;
- the next retest date calculated from the latest attempt;
- recent-first attempt history, including an `in_progress` state.

An empty `current_assessment` is the normal state before a candidate submits a
base assessment. A submitted result with `grade_state: not_confirmed` remains
visible and retains the candidate's declared grade; it is not silently
downgraded. The UI presents that state as “GRADE NOT CONFIRMED”.

Answer keys, assessment prompts, integrity telemetry, email, contacts, DOB,
minor state and consent metadata are never part of this response. Employers
receive the standard `ROLE_REQUIRED` error.

The current implementation projects the process-local assessment repository
used by the bootstrap assessment slice. Persistent assessment history remains
a subsequent storage integration task; the ownership and public projection
contract are kept independent of that repository choice.

Evidence: `backend/tests/test_candidate_dashboard.py` covers empty, verified,
unconfirmed, self-scope and employer-denial behavior. The responsive UI is
The legacy assessment-only UI is retained for the route contract, while the
candidate workspace now mounts the richer Verified Skill Passport from
`frontend/src/components/candidate-skill-passport.tsx`. The same candidate
workspace includes the base assessment flow: specialization/declared-grade
selection, unique generated form, progressive explanations, system scoring,
and a history refresh after submission. See
`frontend/src/components/candidate-assessment.tsx` and
`backend/tests/test_assessments.py` for the authenticated lifecycle and
ownership checks.
