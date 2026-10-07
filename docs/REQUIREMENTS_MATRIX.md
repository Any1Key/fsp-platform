# Requirements matrix

Status: `TODO`, `IN_PROGRESS`, `IMPLEMENTED`, `VERIFIED`, `BLOCKED`.

| ID | Priority | Requirement | Evidence | Status | Evidence path |
|---|---|---|---|---|---|
| CORE-001 | P0 | Reverse recruitment: employer initiates contact with verified candidate | Employer invitation API/UI integration tests and Talent Radar flow | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/employer-talent-radar.tsx |
| CORE-002 | P0 | Category = specialization + verified grade, not resume self-description | Talent Radar category projection/ranking tests + employer UI | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; frontend/src/components/employer-talent-radar.tsx |
| CORE-003 | P0 | Candidates ranked by verified profile; FSP is positive signal | ProofMatch score breakdown and no-FSP ranking tests | VERIFIED | backend/app/discovery.py; backend/app/fsp.py; backend/tests/test_talent_radar.py; backend/tests/test_fsp.py |
| AST-001 | P0 | Onboarding questionnaire for industry/specialization | Candidate E2E | TODO |  |
| AST-002 | P0 | Candidate chooses declared grade | Authenticated candidate assessment UI + API lifecycle tests | VERIFIED | backend/tests/test_assessments.py; frontend/src/components/candidate-assessment.tsx |
| AST-003 | P0 | Working assessment determines employer-visible category | Employer Talent Radar assessment-to-category integration tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py |
| AST-004 | P0 | Assessment resists leaked fixed questions | Variants/anchors implementation | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py |
| AST-005 | P0 | Different forms have comparable difficulty | Blueprint/anchor validation | IN_PROGRESS | backend/tests/test_assessments.py (stable domain shape; calibration validation pending) |
| AST-006 | P0 | Show test formation from several vacancy/need descriptions | Demo data/tests | TODO |  |
| AST-007 | P0 | Failed declared-grade test does not forcibly downgrade | Domain test | TODO |  |
| AST-008 | P0 | Candidate can take lower-grade test | Domain/E2E | TODO |  |
| AST-009 | P0 | Strong result can offer higher-grade test | Domain/E2E | TODO |  |
| AST-010 | P0 | Grade change/retest frequency limited | 90-day configurable test | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py |
| AST-011 | P2 | Periodic short employer challenges | E2E + freshness | TODO |  |
| AST-012 | P0 | Different candidates do not receive identical assessment forms | Form uniqueness property/integration tests | VERIFIED | backend/tests/test_assessments.py; docs/VALIDATION_RESULTS.md |
| AST-013 | P0 | Base grade assessment is scored by the platform/system | Scoring domain tests | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py |
| AST-014 | P0 | Synthetic/labeled validation proves grade discrimination and detects grade collapse | Confusion matrix + grade-collapse report | VERIFIED | backend/tests/test_assessment_validation.py; docs/VALIDATION_RESULTS.md |
| AST-015 | P0 | AI-resistant assessment uses progressive/session-specific controls; no AI detector as sole gate | Progressive/session controls, delayed canonical review, advisory telemetry, deterministic hidden checks and cross-submission text/code similarity tests; no automatic rejection | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py; docs/AI_ASSESSMENT_INTEGRITY.md |
| AST-016 | P0 | Exposure control prevents immediate reusable answer-key leakage | Exposure/version tests | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py |
| CAND-001 | P0 | Candidate profile manual form | Candidate profile API integration tests + responsive UI build | VERIFIED | backend/tests/test_candidate_profile.py; frontend/src/components/candidate-profile.tsx; .agent/runs/20261007-184054-c037/verification.log |
| CAND-002 | P0 | PDF resume upload + extraction | Consent-gated deterministic PDF extraction, provenance/confidence review, explicit accept/reject, profile-write and privacy tests | VERIFIED | backend/tests/test_resume_upload.py; frontend/src/components/candidate-resume.tsx; backend/app/main.py |
| CAND-003 | P0 | Generate standardized PDF profile | Candidate-scoped PDF artifact endpoint/UI, protected-data omission and PDF parsing tests | VERIFIED | backend/tests/test_candidate_profile.py; frontend/src/components/candidate-profile.tsx; docs/PROFILE_PDF.md |
| CAND-004 | P0 | Show category/grade and assessment history | Candidate-scoped dashboard API/UI, verified and unconfirmed state tests, assessment submission refresh | VERIFIED | backend/tests/test_candidate_dashboard.py; frontend/src/components/candidate-dashboard.tsx |
| CAND-005 | P0 | Incoming invitations with salary | Candidate inbox API/UI integration tests with salary visibility | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/candidate-invitations.tsx |
| CAND-006 | P0 | Accept/decline invitation | Candidate-scoped transition tests and inbox actions | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/candidate-invitations.tsx |
| CAND-007 | P2 | Browse vacancies | E2E | TODO |  |
| CAND-008 | P2 | Candidate applies to vacancy | E2E | TODO |  |
| CAND-009 | P2 | Candidate sees application statuses | E2E | TODO |  |
| CAND-010 | P0 | Privacy settings + processing/publication consent | Domain + E2E | VERIFIED | backend/tests/test_auth.py; frontend/src/components/privacy-settings.tsx |
| CAND-011 | P0 | Link profile to FSP ID | Candidate-scoped consent-gated link/read/unlink integration tests + UI | VERIFIED | backend/tests/test_fsp.py; frontend/src/components/candidate-fsp.tsx; docs/FSP_INTEGRATION.md |
| CAND-012 | P0 | Candidate cannot access others' private data | Authorization tests | TODO |  |
| CAND-013 | P0 | Minor candidate can upload private parent/legal-representative consent documentation | Minor-flow API/UI + authorization tests | VERIFIED | backend/tests/test_minor_consent.py; frontend/src/components/candidate-minor-consent.tsx; docs/API_GUIDELINES.md |
| CAND-014 | P0 | Age/minor data is private and excluded from matching | Protected candidate API/UI + self-scope/privacy tests | VERIFIED | backend/tests/test_protected_candidate.py; backend/tests/test_talent_radar.py; backend/app/discovery.py |
| EMP-001 | P0 | Employer company profile | Employer-scoped API/UI, migration, validation and ownership tests | VERIFIED | backend/tests/test_company_profile.py; frontend/src/components/employer-company-profile.tsx; docs/EMPLOYER_COMPANY_PROFILE.md |
| EMP-002 | P0 | Employer hiring need: team/stack/specialization/grade | Employer-scoped API/UI, normalized migration, taxonomy/ownership/validation tests | VERIFIED | backend/tests/test_hiring_need.py; backend/app/hiring_needs.py; frontend/src/components/employer-hiring-need.tsx |
| EMP-003 | P0 | Recommended categories and concrete candidates | Talent Radar category/candidate integration tests + UI | VERIFIED | backend/tests/test_talent_radar.py; frontend/src/components/employer-talent-radar.tsx |
| EMP-004 | P0 | Explain why candidate is recommended | Reasons, breakdown, evidence and gaps API/UI tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; frontend/src/components/employer-talent-radar.tsx |
| EMP-005 | P0 | Search candidate bank | Consent-gated Talent Radar search/filter tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/main.py; frontend/src/components/employer-talent-radar.tsx |
| EMP-006 | P0 | Filters: specialization, grade, category, stack, FSP | Talent Radar taxonomy/skill/FSP filter and snapshot tests | VERIFIED | backend/tests/test_talent_radar.py; frontend/src/components/employer-talent-radar.tsx |
| EMP-007 | P0 | Invitation without mandatory vacancy | Employer create invitation integration test without vacancy dependency | VERIFIED | backend/tests/test_invitations.py; backend/app/invitations.py; docs/INVITATIONS.md |
| EMP-008 | P0 | Invitation has offer + mandatory salary range | Salary range and offer validation tests/UI form | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/employer-talent-radar.tsx; docs/INVITATIONS.md |
| EMP-009 | P0 | Track invitation statuses | Employer status-list API/UI and candidate transition tests | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/employer-invitations.tsx |
| EMP-010 | P2 | Publish/edit vacancies + incoming applications | E2E | TODO |  |
| EMP-011 | P0 | Employer can configure additional ordered hiring stages | Pipeline E2E with ownership, ordering, validation and candidate preview | VERIFIED | backend/tests/test_pipeline.py; backend/app/pipelines.py; frontend/src/components/employer-hiring-pipeline.tsx |
| EMP-012 | P0 | Employer can author job-specific tasks/tests | Employer-only task draft/publish/version API, match-bound candidate assignment/submission integration tests, ownership and validation tests, responsive authoring/candidate UI | VERIFIED | backend/tests/test_employer_tasks.py; backend/tests/test_task_assignments.py; frontend/src/components/employer-task-authoring.tsx; frontend/src/components/candidate-task-assignments.tsx |
| EMP-013 | P0 | Employer is final grader for employer-authored tasks | Employer assignment ownership, immutable-rubric validation, derived score and release integration tests | VERIFIED | backend/tests/test_employer_evaluations.py; backend/app/employer_evaluations.py; frontend/src/components/employer-task-evaluations.tsx |
| EMP-014 | P1 | Local CPU AI can propose employer task/rubric drafts from current need and approved task history | AI-off/AI-on adapter tests | TODO |  |
| EMP-015 | P0 | Employer-specific result does not silently overwrite global verified grade | Candidate dashboard regression before/after employer evaluation and employer-evidence storage test | VERIFIED | backend/tests/test_employer_evaluations.py; backend/alembic/versions/20261007_0018_employer_evaluations.py; docs/EMPLOYER_ASSESSMENTS.md |
| PRIV-001 | P0 | No employer candidate contacts before unlock | Invitation/discovery payload privacy regression tests | VERIFIED | backend/tests/test_invitations.py; backend/app/invitations.py; docs/INVITATIONS.md |
| CHAT-001 | P0 | Neither employer nor candidate can chat before match | Authorization/E2E | VERIFIED | backend/tests/test_chat.py; backend/app/chat.py |
| CHAT-002 | P0 | Accepted invitation creates match and unlocks private internal chat | State-machine E2E | VERIFIED | backend/tests/test_invitations.py; backend/tests/test_chat.py; backend/alembic/versions/20261007_0014_internal_chat.py |
| CHAT-003 | P0 | Matched parties can exchange messages/contacts; outsiders cannot access conversation | Chat authorization E2E | VERIFIED | backend/tests/test_chat.py; backend/app/chat.py |
| CHAT-004 | P1 | Persisted chat has unread state/history and safe logging | UI/API tests | VERIFIED | backend/tests/test_chat.py; docs/CHAT_AND_MATCHING.md |
| MATCH-001 | P0 | Search based on assessed category, not resume keywords | Category-first Talent Radar projection tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; docs/MATCHING_ENGINE.md |
| MATCH-002 | P0 | Within-category rank uses assessment/FSP evidence | Score breakdown and FSP contribution integration tests | VERIFIED | backend/tests/test_talent_radar.py; backend/tests/test_fsp.py; backend/app/discovery.py |
| MATCH-003 | P0 | Rank by employer-need fit | Required/preferred coverage and need-specific ranking tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; docs/MATCHING_ENGINE.md |
| MATCH-004 | P0 | Explainable ranking | Reasons, component scores and evidence UI/API | VERIFIED | backend/tests/test_talent_radar.py; frontend/src/components/employer-talent-radar.tsx |
| MATCH-005 | P0 | Refine/filter without losing prior selection | Filter snapshot IDs/version contract tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; docs/API_GUIDELINES.md |
| MATCH-006 | P0 | Candidate with unconfirmed declared grade remains searchable with clear marker | Unconfirmed visibility/toggle integration test and UI badge | VERIFIED | backend/tests/test_talent_radar.py; frontend/src/components/employer-talent-radar.tsx |
| MATCH-007 | P1 | ProofMatch exposes evidence confidence, freshness, gaps and talent-category context | Explainability response/UI integration tests | VERIFIED | backend/tests/test_talent_radar.py; backend/app/discovery.py; docs/MATCHING_ENGINE.md |
| DATA-001 | P0 | Salary min/max RUB mandatory in vacancy | Validation | TODO |  |
| DATA-002 | P0 | Salary min/max RUB mandatory in invitation | Request/schema and range validation integration tests | VERIFIED | backend/tests/test_invitations.py; backend/app/invitations.py; docs/INVITATIONS.md |
| DATA-003 | P0 | Candidate sees salary before communication | Candidate inbox response/UI test coverage | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/candidate-invitations.tsx |
| DATA-004 | P0 | Invitation contains company + contact method | Company/contact snapshot and inbox integration tests | VERIFIED | backend/tests/test_invitations.py; backend/app/invitations.py; docs/INVITATIONS.md |
| DATA-005 | P0 | Interaction statuses visible to relevant sides | Employer/candidate scoped status API/UI tests | VERIFIED | backend/tests/test_invitations.py; frontend/src/components/employer-invitations.tsx; frontend/src/components/candidate-invitations.tsx |
| AUTH-001 | P0 | Email registration + verification | Keycloak/Mailpit E2E | VERIFIED | qa/tests/auth-registration.spec.ts; .agent/runs/20261007-184054-c037/verification.log:283-311; compose-ps.txt |
| AUTH-002 | P0 | Registration accepts only email domains ending in `.ru` | Identity validation tests | VERIFIED | backend/tests/test_auth.py; backend/app/auth.py; infrastructure/keycloak/realm-fsp.json |
| AUTH-003 | P0 | Working Keycloak/OIDC integration is demonstrated | Demo E2E + JWT/role evidence | VERIFIED | backend/tests/test_auth.py; qa/tests/auth-registration.spec.ts; .agent/runs/20261007-184054-c037/verification.log:289; compose-ps.txt |
| AUTH-004 | P0 | Verified account without a Keycloak application role can complete one-time candidate/employer role onboarding | Signed-token API tests + browser role chooser | VERIFIED | backend/tests/test_auth.py; backend/app/auth.py; frontend/src/components/auth-status.tsx |
| FSP-001 | P0 | Correct no-FSP-history case | Candidate API/UI explicitly returns no-history for no link and empty linked history; integration tests | VERIFIED | backend/tests/test_fsp.py; frontend/src/components/candidate-fsp.tsx; docs/FSP_INTEGRATION.md |
| FSP-002 | P0 | Synthetic replaceable adapter | `FspRegistryPort`, deterministic adapter tests, candidate link API | VERIFIED | backend/app/fsp.py; backend/tests/test_fsp.py; docs/FSP_INTEGRATION.md |
| FSP-003 | P0 | Synthetic FSP achievements are displayed and contribute a bounded positive ranking signal | Deterministic relevance/result/recency/verification scoring, cap/no-history tests, and persisted snapshot integration; branded candidate rendering; employer rendering remains M06 | VERIFIED | backend/app/fsp.py; backend/app/discovery.py; backend/tests/test_fsp.py; frontend/src/components/candidate-fsp.tsx; frontend/src/components/employer-talent-radar.tsx |
| FSP-004 | P0 | Keycloak/FSP identity bridge is demonstrable while keeping platform identity and FSP participant identity separate | Candidate-scoped bridge endpoint/UI exposes issuer, one-way subject fingerprint, explicit-link mode and replaceable adapter contract; raw subject/token disclosure and cross-candidate access tests | VERIFIED | backend/tests/test_fsp.py; backend/app/fsp.py; docs/FSP_INTEGRATION.md |
| VAL-001 | P0 | Own candidate/vacancy dataset | Versioned synthetic generator | TODO |  |
| VAL-002 | P0 | Own validation procedure + real results | Validation suite | TODO |  |
| NFR-001 | P0 | Runs on ordinary machine with reasonable memory | Compose review | TODO |  |
| NFR-002 | P0 | Open unobfuscated source | Repository | TODO |  |
| NFR-003 | P0 | Clear frontend/backend/storage separation | Architecture review + database session boundary tests | VERIFIED | docs/ARCHITECTURE.md; backend/app/db.py; backend/tests/test_database.py |
| NFR-004 | P0 | Reproducible Docker Compose startup | Locked installs, startup migration, and empty-database migration test | VERIFIED | backend/tests/test_migrations.py; .agent/runs/20261007-184054-c037/verification.log:177-199; .agent/runs/20261007-184054-c037/compose-ps.txt |
| NFR-005 | P0 | OpenAPI documents API/errors | OpenAPI audit | VERIFIED | backend/tests/test_errors.py; backend/app/errors.py; docs/API_GUIDELINES.md |
| NFR-006 | P0 | RBAC, secure tokens, consent/privacy | Security tests | TODO |  |
| NFR-007 | P0 | Keycloak compatibility | OIDC implementation | VERIFIED | backend/app/auth.py; backend/tests/test_auth.py; qa/tests/auth-registration.spec.ts; compose-ps.txt |
| NFR-008 | P0 | Modern desktop browsers | Playwright | TODO |  |
| NFR-009 | P1 | Responsive tablet/mobile (project upgrades optional item) | Responsive E2E/screenshots | TODO |  |
| NFR-010 | P0 | Stable for tens of concurrent users with reproducible load test | Target load-test report | TODO |  |
| NFR-011 | P0 | Core system requires no GPU and targets ~8 CPU / 32–64 GB RAM | Deployment/resource test | VERIFIED | docker-compose.yml; docs/PERFORMANCE_RESULTS.md; .agent/runs/20261006-m00-resource-baseline-rerun/performance/summary.txt; .agent/runs/20261006-m00-resource-baseline-rerun/performance/host-specs.txt |
| NFR-012 | P1 | Optional local AI is isolated, asynchronous and has deterministic fallback | Failure/fallback tests | TODO |  |
| NFR-013 | P0 | Automated CI validates locked backend/frontend/QA toolchains and Compose configuration | GitHub Actions workflow + CI contract test | VERIFIED | .github/workflows/ci.yml; agent/test-ci-contract.sh; .agent/runs/20261007-184054-c037/verification.log:12-16 |
| LEGAL-001 | P0 | 152-FZ-oriented data minimization, consent, RBAC and audit controls are documented/implemented | Security/privacy audit | TODO |  |
| LEGAL-002 | P1 | Withdrawal/deletion/export/retention workflows or demonstrable MVP concepts exist | Privacy E2E/docs | VERIFIED | backend/app/privacy.py; backend/tests/test_auth.py; docs/API_GUIDELINES.md; docs/SECURITY.md |
| LEGAL-003 | P0 | Telegram agent reporting never sends real PII/chat/minor documents | Reporter tests/config audit | TODO |  |
| DOC-001 | P0 | Architecture docs | Docs audit | TODO |  |
| DOC-002 | P0 | Assessment/leak-resistance docs | Docs audit | TODO |  |
| DOC-003 | P0 | Matching/category docs | Matching engine, Talent Radar API contract and employer UI docs | VERIFIED | docs/MATCHING_ENGINE.md; docs/API_GUIDELINES.md; frontend/src/components/employer-talent-radar.tsx |
| DOC-004 | P0 | Validation procedure/results docs | Docs audit | TODO |  |
| DOC-005 | P0 | FSP integration scheme docs | Docs audit | VERIFIED | docs/FSP_INTEGRATION.md; docs/DATA_MODEL.md; backend/app/fsp.py |
| DOC-006 | P0 | API description | OpenAPI/docs | VERIFIED | docs/API_GUIDELINES.md; backend/tests/test_errors.py; backend/app/main.py |
| DOC-007 | P0 | Libraries/components with versions | COMPONENTS.md | VERIFIED | docs/COMPONENTS.md; backend/requirements.lock; frontend/package-lock.json; qa/package-lock.json; docker-compose.yml |
| DOC-008 | P0 | Step-by-step build/deploy/local run | Setup/deployment docs | VERIFIED | docs/DEPLOYMENT.md; .env.example; scripts/demo-reset.sh |
| DEMO-001 | P0 | Full candidate→assessment→employer→contact demo | Playwright + demo reset | TODO |  |
| BONUS-001 | P2 | Fake-vacancy / bad-employer protection concept/MVP | Trust design | TODO |  |
| BONUS-002 | P2 | ATS integration concept | Docs/contract | TODO |  |
| INNOV-001 | P2 | Verified Skill Passport | UI/domain | TODO |  |
| INNOV-002 | P2 | Evidence freshness | Domain/UI | TODO |  |
| INNOV-003 | P2 | Blind Discovery | Privacy/UI | TODO |  |
| INNOV-004 | P2 | Talent Radar | Employer UI | TODO |  |
| INNOV-005 | P2 | Assessment Integrity signals | Advisory telemetry, hidden-check and cross-submission similarity signals rendered in candidate result UI | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py; frontend/src/components/candidate-assessment.tsx; docs/AI_ASSESSMENT_INTEGRITY.md |
| INNOV-006 | P2 | Career Graph | Candidate UI | TODO |  |
| INNOV-007 | P2 | Validation Dashboard | Demo UI | TODO |  |
| INNOV-008 | P1 | Deterministic Jury Demo reset | Script/E2E | TODO |  |
