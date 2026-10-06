# Product specification

## 1. Product thesis

FSP Talent Platform is a two-sided IT talent marketplace centered on **reverse recruitment** and **verified evidence**. Candidates establish a professional category through assessment and evidence; employers explore talent categories, receive explainable recommendations and initiate contact with a concrete salary range.

A self-written resume is context, but it does not define the employer-visible verified category.

The distinctive product mechanic is **ProofMatch / Evidence-Graph Reverse Matching**: the employer starts from a hiring need and talent category, then sees candidates ranked by verified, recent, job-relevant evidence with explicit reasons and gaps.

## 2. Roles

### Candidate
Must be able to:
- register by verified email whose domain ends in `.ru`;
- create/edit profile manually;
- upload PDF resume and review parsed fields before saving;
- generate a standardized downloadable profile PDF;
- choose industry/specialization and declared grade;
- take a unique per-attempt base grade assessment;
- see current category, declared grade, confirmation state, score/confidence, history and retest availability;
- remain discoverable when the declared grade is not confirmed, with a prominent employer-visible “grade not confirmed” marker;
- link/unlink demo FSP ID and view FSP evidence when present;
- work correctly with no FSP history;
- manage profile visibility and processing/publication consent;
- if a minor, upload required parent/legal-representative consent documentation through a private workflow;
- receive employer invitations with company, offer and mandatory salary range;
- accept/decline invitations;
- after a match, use internal chat and participate in employer-specific hiring stages;
- see only own private interactions.

Extended target:
- browse published vacancies and apply;
- see application statuses;
- complete periodic short challenges.

### Employer
Must be able to:
- maintain company profile;
- describe a hiring need: team, role, specialization, grade, required/preferred stack;
- discover recommended talent categories / Talent Radar;
- browse/rank candidates, including clearly marked unconfirmed-grade candidates;
- see why every candidate was recommended, what is verified and what is missing;
- filter/refine without losing the current result context;
- send an invitation with salary range and offer without requiring a published vacancy;
- track invitation status;
- never chat with candidate before a match;
- after match, use internal chat;
- create an ordered hiring pipeline with extra tasks/stages;
- author and grade employer-specific tasks;
- optionally request CPU-local AI draft tasks based on current need and the employer's own previously approved task library.

Extended target:
- publish/edit vacancies;
- manage incoming applications;
- trust/anti-fraud signals;
- ATS integration concept.

## 3. Core journeys

Candidate:
`register .ru email → verify → consent/privacy → profile/resume → specialization → declared grade → unique assessment → verified/unconfirmed state → discoverability → employer invitation → candidate accepts → MATCH → chat/contact unlock → optional employer stages`

Employer:
`register .ru email → company profile → hiring need → Talent Radar/categories → ProofMatch ranking → explanation → profile → invitation + salary → accepted MATCH → chat → employer pipeline/tasks`

These journeys are demo blockers.

## 4. Taxonomy

Initial specializations:
- Backend Engineering
- Frontend Engineering
- Full-stack Engineering
- QA / Test Automation
- DevOps / SRE
- Data Engineering
- Data Science / ML
- Mobile Engineering

Initial grades:
- Junior
- Middle
- Senior

Taxonomy must be data-driven.

## 5. Grade states

Keep declared grade separate from verified state:
- `declared_unverified`;
- `verified`;
- `not_confirmed`;
- `eligible_for_lower_test`;
- `eligible_for_higher_test`;
- `retest_locked_until`.

A failed declared-grade assessment does **not** hide the candidate and does not forcibly rewrite the declared grade. Employer-facing UI must clearly distinguish verified vs unconfirmed grade.

Grade/retest frequency is configurable; default project policy remains 90 days until organizer says otherwise.

## 6. Evidence model

A skill may have evidence from:
- resume/profile (declared, low trust);
- platform assessment;
- FSP achievement;
- employer challenge/task;
- periodic short challenge.

The product visually distinguishes **declared**, **platform-verified**, **FSP-verified** and **employer-specific** evidence.

Each evidence record has source, skill, score/level, confidence, timestamp, relevance and provenance.

## 7. Assessment

Base platform assessment is system-scored and must be:
- unique per attempt/candidate;
- comparable in difficulty;
- resistant to leaked tasks/answers;
- AI-resistant by design rather than dependent on unreliable AI detectors;
- reproducible/auditable.

Use calibrated blueprints, template families, secure parameterization, anchor items, exposure controls, progressive follow-ups and deterministic rubrics. See `ASSESSMENT_ENGINE.md` and `AI_ASSESSMENT_INTEGRITY.md`.

## 8. Employer hiring pipeline

Employer may add ordered additional stages. Employer-authored tests are graded by the employer. Results are employer-specific evidence by default and do not silently change the global verified grade.

Local AI may draft tasks/rubrics but employer must approve before publishing. Core system works with AI disabled.

## 9. FSP evidence

FSP is a bounded positive signal, not a hard requirement. MVP uses a synthetic replaceable adapter because real API/schema are unavailable.

Synthetic achievement examples may include competition/event name, level, discipline, placement/result, date and verification provenance. Relevance to the hiring need and recency can affect the bounded FSP component of ranking.

“No FSP history” is a normal supported state and never excludes a candidate.

## 10. ProofMatch / Evidence-Graph Reverse Matching

Matching is multi-stage:
1. discoverable candidate/category eligibility;
2. specialization/grade state;
3. required/preferred skill evidence coverage;
4. evidence confidence/freshness;
5. assessment strength;
6. bounded FSP achievement bonus;
7. employer-specific evidence when it exists.

Return score breakdown, reasons, gaps and confidence. Candidate search starts from verified talent categories / Talent Radar rather than a flat resume feed.

Unconfirmed-grade candidates remain visible in a separate clearly labeled lane/ranking state.

## 11. Invitation, match and chat

Minimum invitation states:
- `sent`
- `viewed`
- `accepted`
- `declined`

`accepted` creates a match for the reverse-recruitment path.

Before match: no direct chat.
After match: internal chat is enabled and contact unlock occurs according to the source requirement. Candidate-initiated accepted application may create an equivalent match.

## 12. Salary

Every invitation and vacancy requires:
- `salary_min_rub`
- `salary_max_rub`
- validation `0 < min <= max`.

Candidate sees salary before communication/match.

## 13. Identity / Keycloak

Use working Keycloak/OIDC in the demo where practical:
- email verification;
- candidate/employer roles;
- Authorization Code + PKCE;
- backend JWT validation;
- demonstrable future FSP identity/linking boundary.

Registration must reject emails whose domain does not end in `.ru`.

## 14. Minor candidate support

Age is private and excluded from ranking. Below configurable adult threshold, require a private parent/legal-representative consent-document workflow before profile publication/discoverability. Exact legal wording is configurable and requires legal review.

## 15. Performance / deployment

No GPU requirement. Core must run on a roughly 8 CPU / 32–64 GB RAM host. Optional local AI is isolated and asynchronous. Final service must have reproducible load-test results.

## 16. Differentiating features

After core stability:
- Verified Skill Passport;
- Evidence freshness;
- Blind Discovery;
- Talent Radar;
- ProofMatch evidence graph + confidence/gap explanation;
- Assessment Integrity signals;
- Career Graph;
- employer Hiring Pipeline;
- local-AI task copilot using employer task memory;
- Validation Dashboard;
- deterministic Jury Demo Mode.

## 17. Non-goals

- third-party job-site scraping;
- mandatory microservices;
- invented production FSP API integration;
- GPU-dependent operation;
- fully automated hiring decisions;
- automatic cheating accusation based on AI detection;
- ranking using protected/sensitive traits;
- invasive proctoring for MVP.
