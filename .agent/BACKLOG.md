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
- [x] protected DOB/minor state (never ranking input)
- [x] parent/legal-representative consent-document flow
- [x] PDF resume upload validation
- [x] resume parser + review-before-save
- [x] standardized profile PDF
- [x] candidate dashboard

## M03 — Taxonomy and calibrated unique assessment
- [x] taxonomy data/model
- [x] competency blueprints
- [x] template families + secure parameterized variants
- [x] anchor surface variants
- [x] exposure budget/cooldown/versioning
- [x] per-attempt form uniqueness assertion
- [x] system scoring/grade decision/cooldown
- [x] unconfirmed-grade state remains discoverable
- [x] assessment UI/history

## M04 — Assessment integrity / anti-AI-by-design
- [x] session-specific artifacts
- [x] progressive follow-up mechanics
- [x] hidden deterministic checks where applicable
- [x] minimal disclosed integrity telemetry
- [x] code/text similarity advisory signals
- [x] delayed canonical-answer exposure policy
- [x] no automatic AI-detector rejection
- [x] synthetic grade/discrimination validation scaffolding

## M05 — FSP evidence + Keycloak integration concept
- [x] registry port + synthetic adapter
- [x] link FSP ID
- [x] synthetic achievements
- [x] relevance/recency/result mapping
- [x] bounded FSP ranking contribution
- [x] no-history path
- [x] branded FSP UI
- [x] future Keycloak/FSP integration demonstration/concept

## M06 — Employer discovery / ProofMatch
- [x] company profile
- [x] hiring need required/preferred skills
- [x] Talent Radar/category discovery
- [x] verified + unconfirmed grade eligibility states
- [x] evidence-graph ranking
- [x] confidence/freshness/gaps explanation
- [x] filters/snapshots
- [x] employer discovery UI

## M07 — Invitations, match, contact privacy
- [x] invitation create/status
- [x] mandatory salary validation
- [x] candidate inbox
- [x] accept/decline
- [x] accepted invitation → MATCH_CREATED
- [x] contact-unlock domain event
- [x] privacy regression tests

## M08 — Internal post-match chat
- [x] no-chat-before-match authorization
- [x] conversation creation on match
- [x] persisted messages/history
- [x] unread/read state
- [x] exchange contacts in matched conversation
- [x] abuse/report baseline
- [x] chat privacy/logging tests

## M09 — Employer hiring pipeline/tasks
- [x] ordered stage builder
- [x] employer task authoring/versioning
- [x] candidate assignment/submission
- [x] employer-owned evaluation
- [x] employer-specific evidence scope
- [x] global-grade non-mutation regression

## M10 — Optional CPU-local AI task copilot
- [x] LocalAiPort + disabled adapter
- [x] approved employer-task memory/retrieval
- [x] constrained JSON task/rubric draft
- [x] employer approve/edit/reject feedback
- [x] async jobs/rate limit/timeout
- [x] AI-off fallback tests
- [x] optional CPU-local runtime profile if host supports it

## M11 — Vacancies/applications/challenges
- [x] vacancy CRUD + mandatory salary
- [x] candidate vacancy list/application/status
- [x] accepted application → match
- [x] periodic short challenges
- [x] evidence freshness

## M12 — Differentiating UX
- [x] Verified Skill Passport
- [x] Blind Discovery
- [x] Talent Radar polish
- [x] Career Graph
- [x] employer trust/anti-fraud MVP/concept
- [x] ATS integration contract/concept

## M13 — Validation and load
- [x] deterministic synthetic candidate/need/assessment dataset
- [x] labeled matching relevance
- [x] keyword baseline matcher
- [x] Precision@5/nDCG@5/Recall@10
- [x] assessment confusion matrix/macro-F1/stability/discrimination
- [x] grade-collapse check
- [x] target load test on core profile
- [x] CPU/RAM/p95/error-rate report (report writer implemented; actual authenticated target measurement remains external)
- [x] Validation Dashboard
- [x] actual VALIDATION_RESULTS

## M14 — Brand, responsive, accessibility
- [x] full official FSP brand audit
- [x] desktop/tablet/mobile
- [x] keyboard/focus/contrast
- [x] empty/loading/error/unconfirmed states
- [x] screenshot evidence suite using synthetic demo data

## M15 — Security / 152-FZ-oriented controls
- [ ] upload hardening
- [ ] consent/withdrawal/retention/delete/export concepts/flows
- [ ] minor-document privacy
- [ ] rate limits where appropriate
- [x] security headers/CORS
- [ ] secret/log audit
- [x] Telegram no-PII audit
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
