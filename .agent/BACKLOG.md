# Autonomous backlog

Markers: `[ ] TODO`, `[~] IN_PROGRESS`, `[x] IMPLEMENTED`, `[v] VERIFIED`, `[!] BLOCKED`.

## M00 — Foundation
- [x] dependency locks and migrations
- [x] DB/session infrastructure
- [x] API error envelope/request IDs
- [x] CI baseline
- [x] CPU-only resource baseline

## M01 — Keycloak identity, .ru registration, roles, consent
- [x] working candidate/employer sign-in via Keycloak
- [x] email verification via Mailpit
- [x] reject non-`.ru` registration email
- [x] role onboarding
- [x] consent/privacy
- [x] Keycloak/JWT demo evidence
- [x] authorization integration tests

## M02 — Candidate profile, resume, minor flow
- [x] manual profile
- [ ] protected DOB/minor state (never ranking input)
- [ ] parent/legal-representative consent-document flow
- [ ] PDF resume upload validation
- [ ] resume parser + review-before-save
- [ ] standardized profile PDF
- [ ] candidate dashboard

## M03 — Taxonomy and calibrated unique assessment
- [ ] taxonomy data/model
- [x] competency blueprints
- [x] template families + secure parameterized variants
- [x] anchor surface variants
- [x] exposure budget/cooldown/versioning
- [x] per-attempt form uniqueness assertion
- [x] system scoring/grade decision/cooldown
- [x] unconfirmed-grade state remains discoverable
- [ ] assessment UI/history

## M04 — Assessment integrity / anti-AI-by-design
- [x] session-specific artifacts
- [x] progressive follow-up mechanics
- [ ] hidden deterministic checks where applicable
- [x] minimal disclosed integrity telemetry
- [ ] code/text similarity advisory signals
- [ ] delayed canonical-answer exposure policy
- [x] no automatic AI-detector rejection
- [ ] synthetic grade/discrimination validation scaffolding

## M05 — FSP evidence + Keycloak integration concept
- [ ] registry port + synthetic adapter
- [ ] link FSP ID
- [ ] synthetic achievements
- [ ] relevance/recency/result mapping
- [ ] bounded FSP ranking contribution
- [ ] no-history path
- [ ] branded FSP UI
- [ ] future Keycloak/FSP integration demonstration/concept

## M06 — Employer discovery / ProofMatch
- [ ] company profile
- [ ] hiring need required/preferred skills
- [ ] Talent Radar/category discovery
- [ ] verified + unconfirmed grade eligibility states
- [ ] evidence-graph ranking
- [ ] confidence/freshness/gaps explanation
- [ ] filters/snapshots
- [ ] employer discovery UI

## M07 — Invitations, match, contact privacy
- [ ] invitation create/status
- [ ] mandatory salary validation
- [ ] candidate inbox
- [ ] accept/decline
- [ ] accepted invitation → MATCH_CREATED
- [ ] contact-unlock domain event
- [ ] privacy regression tests

## M08 — Internal post-match chat
- [ ] no-chat-before-match authorization
- [ ] conversation creation on match
- [ ] persisted messages/history
- [ ] unread/read state
- [ ] exchange contacts in matched conversation
- [ ] abuse/report baseline
- [ ] chat privacy/logging tests

## M09 — Employer hiring pipeline/tasks
- [ ] ordered stage builder
- [ ] employer task authoring/versioning
- [ ] candidate assignment/submission
- [ ] employer-owned evaluation
- [ ] employer-specific evidence scope
- [ ] global-grade non-mutation regression

## M10 — Optional CPU-local AI task copilot
- [ ] LocalAiPort + disabled adapter
- [ ] approved employer-task memory/retrieval
- [ ] constrained JSON task/rubric draft
- [ ] employer approve/edit/reject feedback
- [ ] async jobs/rate limit/timeout
- [ ] AI-off fallback tests
- [ ] optional CPU-local runtime profile if host supports it

## M11 — Vacancies/applications/challenges
- [ ] vacancy CRUD + mandatory salary
- [ ] candidate vacancy list/application/status
- [ ] accepted application → match
- [ ] periodic short challenges
- [ ] evidence freshness

## M12 — Differentiating UX
- [ ] Verified Skill Passport
- [ ] Blind Discovery
- [ ] Talent Radar polish
- [ ] Career Graph
- [ ] employer trust/anti-fraud MVP/concept
- [ ] ATS integration contract/concept

## M13 — Validation and load
- [ ] deterministic synthetic candidate/need/assessment dataset
- [ ] labeled matching relevance
- [ ] keyword baseline matcher
- [ ] Precision@5/nDCG@5/Recall@10
- [ ] assessment confusion matrix/macro-F1/stability/discrimination
- [ ] grade-collapse check
- [ ] target load test on core profile
- [ ] CPU/RAM/p95/error-rate report
- [ ] Validation Dashboard
- [ ] actual VALIDATION_RESULTS

## M14 — Brand, responsive, accessibility
- [ ] full official FSP brand audit
- [ ] desktop/tablet/mobile
- [ ] keyboard/focus/contrast
- [ ] empty/loading/error/unconfirmed states
- [ ] screenshot evidence suite using synthetic demo data

## M15 — Security / 152-FZ-oriented controls
- [ ] upload hardening
- [ ] consent/withdrawal/retention/delete/export concepts/flows
- [ ] minor-document privacy
- [ ] rate limits where appropriate
- [ ] security headers/CORS
- [ ] secret/log audit
- [ ] Telegram no-PII audit
- [ ] index/query audit

## M16 — Submission/docs/demo
- [ ] OpenAPI audit
- [ ] docs current
- [ ] dependency versions
- [ ] deploy from clean clone
- [ ] deterministic demo reset
- [ ] complete jury E2E
- [ ] presentation-source outline

## M17 — Final independent audit
- [ ] requirements audit
- [ ] defect triage P0/P1/P2
- [ ] fix P0/P1
- [ ] fresh CPU-only deployment
- [ ] final load run
- [ ] final responsive screenshots/evidence
- [ ] set READY only after external acceptance
