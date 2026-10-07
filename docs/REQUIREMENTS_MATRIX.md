# Requirements matrix

Status: `TODO`, `IN_PROGRESS`, `IMPLEMENTED`, `VERIFIED`, `BLOCKED`.

| ID | Priority | Requirement | Evidence | Status | Evidence path |
|---|---|---|---|---|---|
| CORE-001 | P0 | Reverse recruitment: employer initiates contact with verified candidate | E2E employer discovery → invitation | TODO |  |
| CORE-002 | P0 | Category = specialization + verified grade, not resume self-description | Backend tests + UI evidence | TODO |  |
| CORE-003 | P0 | Candidates ranked by verified profile; FSP is positive signal | Ranking tests | TODO |  |
| AST-001 | P0 | Onboarding questionnaire for industry/specialization | Candidate E2E | TODO |  |
| AST-002 | P0 | Candidate chooses declared grade | Authenticated candidate assessment UI + API lifecycle tests | IMPLEMENTED | frontend/src/components/candidate-assessment.tsx; backend/tests/test_assessments.py |
| AST-003 | P0 | Working assessment determines employer-visible category | Assessment integration tests | IN_PROGRESS | backend/tests/test_assessments.py (assessment result only; employer wiring pending); taxonomy catalog boundary implemented in backend/app/taxonomy.py and backend/tests/test_taxonomy.py |
| AST-004 | P0 | Assessment resists leaked fixed questions | Variants/anchors implementation | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py; docs/AI_ASSESSMENT_INTEGRITY.md |
| AST-005 | P0 | Different forms have comparable difficulty | Blueprint/anchor validation | IN_PROGRESS | backend/tests/test_assessments.py (stable domain shape; calibration validation pending) |
| AST-006 | P0 | Show test formation from several vacancy/need descriptions | Demo data/tests | TODO |  |
| AST-007 | P0 | Failed declared-grade test does not forcibly downgrade | Domain test | TODO |  |
| AST-008 | P0 | Candidate can take lower-grade test | Domain/E2E | TODO |  |
| AST-009 | P0 | Strong result can offer higher-grade test | Domain/E2E | TODO |  |
| AST-010 | P0 | Grade change/retest frequency limited | 90-day configurable test | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py |
| AST-011 | P2 | Periodic short employer challenges | E2E + freshness | TODO |  |
| AST-012 | P0 | Different candidates do not receive identical assessment forms | Form uniqueness property/integration tests | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py; backend/tests/test_assessment_validation.py; docs/VALIDATION_RESULTS.md |
| AST-013 | P0 | Base grade assessment is scored by the platform/system | Scoring domain tests | VERIFIED | backend/tests/test_assessments.py; backend/app/assessments.py; .agent/runs/20261007-045717-c022/verification.log |
| AST-014 | P0 | Synthetic/labeled validation proves grade discrimination and detects grade collapse | Confusion matrix + grade-collapse report | VERIFIED | backend/app/assessment_validation.py; backend/tests/test_assessment_validation.py; docs/VALIDATION_RESULTS.md |
| AST-015 | P0 | AI-resistant assessment uses progressive/session-specific controls; no AI detector as sole gate | Progressive/session controls, delayed canonical review, advisory telemetry, deterministic hidden checks and cross-submission text/code similarity tests; no automatic rejection | VERIFIED | backend/tests/test_assessments.py:48-193,196-211,235-274; backend/app/assessments.py; frontend/src/components/candidate-assessment.tsx; docs/AI_ASSESSMENT_INTEGRITY.md |
| AST-016 | P0 | Exposure control prevents immediate reusable answer-key leakage | Exposure/version tests | VERIFIED | backend/app/assessments.py; backend/tests/test_assessments.py; docs/API_GUIDELINES.md |
| CAND-001 | P0 | Candidate profile manual form | Candidate profile API integration tests + responsive UI build | VERIFIED | backend/app/candidates.py; backend/app/main.py:484-514; backend/tests/test_candidate_profile.py; frontend/src/components/candidate-profile.tsx; frontend/src/components/auth-status.tsx:144-146 |
| CAND-002 | P0 | PDF resume upload + extraction | Consent-gated deterministic PDF extraction, provenance/confidence review, explicit accept/reject, profile-write and privacy tests | IMPLEMENTED | backend/app/resume_parser.py; backend/app/resume.py; backend/alembic/versions/20261007_0007_resume_extraction.py; backend/tests/test_resume_upload.py; frontend/src/components/candidate-resume.tsx; docs/RESUME_PARSING.md |
| CAND-003 | P0 | Generate standardized PDF profile | Candidate-scoped PDF artifact endpoint/UI, protected-data omission and PDF parsing tests | IMPLEMENTED | backend/app/profile_pdf.py; backend/app/main.py; backend/tests/test_candidate_profile.py; frontend/src/components/candidate-profile.tsx; docs/PROFILE_PDF.md |
| CAND-004 | P0 | Show category/grade and assessment history | Candidate-scoped dashboard API/UI, verified and unconfirmed state tests, assessment submission refresh | IMPLEMENTED | backend/app/main.py; backend/tests/test_candidate_dashboard.py; frontend/src/components/candidate-dashboard.tsx; frontend/src/components/candidate-assessment.tsx; docs/CANDIDATE_DASHBOARD.md |
| CAND-005 | P0 | Incoming invitations with salary | E2E | TODO |  |
| CAND-006 | P0 | Accept/decline invitation | E2E | TODO |  |
| CAND-007 | P2 | Browse vacancies | E2E | TODO |  |
| CAND-008 | P2 | Candidate applies to vacancy | E2E | TODO |  |
| CAND-009 | P2 | Candidate sees application statuses | E2E | TODO |  |
| CAND-010 | P0 | Privacy settings + processing/publication consent | Domain + E2E | VERIFIED | backend/app/privacy.py; backend/tests/test_auth.py:220-303; frontend/src/components/privacy-settings.tsx; frontend/src/components/auth-status.tsx:144-146 |
| CAND-011 | P0 | Link profile to FSP ID | Adapter/E2E | TODO |  |
| CAND-012 | P0 | Candidate cannot access others' private data | Authorization tests | TODO |  |
| CAND-013 | P0 | Minor candidate can upload private parent/legal-representative consent documentation | Minor-flow API/UI + authorization tests | VERIFIED | backend/app/minor_consent.py; backend/tests/test_minor_consent.py; frontend/src/components/candidate-minor-consent.tsx; frontend/src/components/candidate-protected-profile.tsx; docs/API_GUIDELINES.md:88-100 |
| CAND-014 | P0 | Age/minor data is private and excluded from matching | Protected candidate API/UI + self-scope/privacy tests | IMPLEMENTED | backend/app/protected_candidate.py; backend/app/main.py; backend/tests/test_protected_candidate.py; frontend/src/components/candidate-protected-profile.tsx; docs/SECURITY.md |
| EMP-001 | P0 | Employer company profile | E2E | TODO |  |
| EMP-002 | P0 | Employer hiring need: team/stack/specialization/grade | E2E | TODO |  |
| EMP-003 | P0 | Recommended categories and concrete candidates | Matching E2E | TODO |  |
| EMP-004 | P0 | Explain why candidate is recommended | API/UI | TODO |  |
| EMP-005 | P0 | Search candidate bank | E2E | TODO |  |
| EMP-006 | P0 | Filters: specialization, grade, category, stack, FSP | E2E | TODO |  |
| EMP-007 | P0 | Invitation without mandatory vacancy | E2E | TODO |  |
| EMP-008 | P0 | Invitation has offer + mandatory salary range | Validation/E2E | TODO |  |
| EMP-009 | P0 | Track invitation statuses | E2E | TODO |  |
| EMP-010 | P2 | Publish/edit vacancies + incoming applications | E2E | TODO |  |
| EMP-011 | P0 | Employer can configure additional ordered hiring stages | Pipeline E2E | TODO |  |
| EMP-012 | P0 | Employer can author job-specific tasks/tests | Employer task E2E | TODO |  |
| EMP-013 | P0 | Employer is final grader for employer-authored tasks | Authorization/domain tests | TODO |  |
| EMP-014 | P1 | Local CPU AI can propose employer task/rubric drafts from current need and approved task history | AI-off/AI-on adapter tests | TODO |  |
| EMP-015 | P0 | Employer-specific result does not silently overwrite global verified grade | Domain regression test | TODO |  |
| PRIV-001 | P0 | No employer candidate contacts before unlock | Security integration tests | TODO |  |
| CHAT-001 | P0 | Neither employer nor candidate can chat before match | Authorization/E2E | TODO |  |
| CHAT-002 | P0 | Accepted invitation creates match and unlocks private internal chat | State-machine E2E | TODO |  |
| CHAT-003 | P0 | Matched parties can exchange messages/contacts; outsiders cannot access conversation | Chat authorization E2E | TODO |  |
| CHAT-004 | P1 | Persisted chat has unread state/history and safe logging | UI/API tests | TODO |  |
| MATCH-001 | P0 | Search based on assessed category, not resume keywords | Ranking tests | TODO |  |
| MATCH-002 | P0 | Within-category rank uses assessment/FSP evidence | Ranking tests | TODO |  |
| MATCH-003 | P0 | Rank by employer-need fit | Metric tests | TODO |  |
| MATCH-004 | P0 | Explainable ranking | API/UI | TODO |  |
| MATCH-005 | P0 | Refine/filter without losing prior selection | Snapshot tests | TODO |  |
| MATCH-006 | P0 | Candidate with unconfirmed declared grade remains searchable with clear marker | Matching/UI E2E | TODO |  |
| MATCH-007 | P1 | ProofMatch exposes evidence confidence, freshness, gaps and talent-category context | Ranking/UI tests | TODO |  |
| DATA-001 | P0 | Salary min/max RUB mandatory in vacancy | Validation | TODO |  |
| DATA-002 | P0 | Salary min/max RUB mandatory in invitation | Validation | TODO |  |
| DATA-003 | P0 | Candidate sees salary before communication | E2E | TODO |  |
| DATA-004 | P0 | Invitation contains company + contact method | E2E | TODO |  |
| DATA-005 | P0 | Interaction statuses visible to relevant sides | E2E | TODO |  |
| AUTH-001 | P0 | Email registration + verification | Keycloak/Mailpit E2E | VERIFIED | qa/tests/auth-registration.spec.ts; .agent/runs/20261007-045717-c022/verification.log; .agent/runs/20261007-045717-c022/compose-ps.txt |
| AUTH-002 | P0 | Registration accepts only email domains ending in `.ru` | Identity validation tests | VERIFIED | backend/tests/test_auth.py; backend/app/auth.py; infrastructure/keycloak/realm-fsp.json |
| AUTH-003 | P0 | Working Keycloak/OIDC integration is demonstrated | Demo E2E + JWT/role evidence | VERIFIED | backend/tests/test_auth.py; qa/tests/auth-registration.spec.ts; .agent/runs/20261007-045717-c022/verification.log |
| AUTH-004 | P0 | Verified account without a Keycloak application role can complete one-time candidate/employer role onboarding | Signed-token API tests + browser role chooser | VERIFIED | backend/app/auth.py:123-235; backend/app/main.py:351-389; backend/tests/test_auth.py:74-130 |
| FSP-001 | P0 | Correct no-FSP-history case | Ranking/E2E | TODO |  |
| FSP-002 | P0 | Synthetic replaceable adapter | Architecture/tests | TODO |  |
| FSP-003 | P0 | Synthetic FSP achievements are displayed and contribute a bounded positive ranking signal | FSP ranking/UI tests | TODO |  |
| VAL-001 | P0 | Own candidate/vacancy dataset | Versioned synthetic generator | TODO |  |
| VAL-002 | P0 | Own validation procedure + real results | Validation suite | TODO |  |
| NFR-001 | P0 | Runs on ordinary machine with reasonable memory | Compose review | TODO |  |
| NFR-002 | P0 | Open unobfuscated source | Repository | TODO |  |
| NFR-003 | P0 | Clear frontend/backend/storage separation | Architecture review + database session boundary tests | VERIFIED | docs/ARCHITECTURE.md; docker-compose.yml; backend/app/db.py; backend/tests/test_database.py |
| NFR-004 | P0 | Reproducible Docker Compose startup | Locked installs, startup migration, and empty-database migration test | VERIFIED | backend/tests/test_migrations.py; .agent/runs/20261007-045717-c022/verification.log; .agent/runs/20261007-045717-c022/compose-ps.txt |
| NFR-005 | P0 | OpenAPI documents API/errors | OpenAPI audit | VERIFIED | backend/tests/test_errors.py; backend/app/errors.py; docs/API_GUIDELINES.md |
| NFR-006 | P0 | RBAC, secure tokens, consent/privacy | Security tests | TODO |  |
| NFR-007 | P0 | Keycloak compatibility | OIDC implementation | VERIFIED | backend/app/auth.py; infrastructure/keycloak/realm-fsp.json; backend/tests/test_auth.py; qa/tests/auth-registration.spec.ts |
| NFR-008 | P0 | Modern desktop browsers | Playwright | TODO |  |
| NFR-009 | P1 | Responsive tablet/mobile (project upgrades optional item) | Responsive E2E/screenshots | TODO |  |
| NFR-010 | P0 | Stable for tens of concurrent users with reproducible load test | Target load-test report | TODO |  |
| NFR-011 | P0 | Core system requires no GPU and targets ~8 CPU / 32–64 GB RAM | Deployment/resource test | VERIFIED | docs/PERFORMANCE_RESULTS.md; .agent/runs/20261006-m00-resource-baseline-rerun/performance/host-specs.txt; .agent/runs/20261006-m00-resource-baseline-rerun/performance/summary.txt; .agent/runs/20261006-m00-resource-baseline-rerun/performance/policy.txt |
| NFR-012 | P1 | Optional local AI is isolated, asynchronous and has deterministic fallback | Failure/fallback tests | TODO |  |
| NFR-013 | P0 | Automated CI validates locked backend/frontend/QA toolchains and Compose configuration | GitHub Actions workflow + CI contract test | VERIFIED | .github/workflows/ci.yml; agent/test-ci-contract.sh; .agent/runs/20261007-045717-c022/verification.log |
| LEGAL-001 | P0 | 152-FZ-oriented data minimization, consent, RBAC and audit controls are documented/implemented | Security/privacy audit | TODO |  |
| LEGAL-002 | P1 | Withdrawal/deletion/export/retention workflows or demonstrable MVP concepts exist | Privacy E2E/docs | VERIFIED | backend/tests/test_auth.py; backend/app/privacy.py; docs/API_GUIDELINES.md; docs/SECURITY.md |
| LEGAL-003 | P0 | Telegram agent reporting never sends real PII/chat/minor documents | Reporter tests/config audit | TODO |  |
| DOC-001 | P0 | Architecture docs | Docs audit | TODO |  |
| DOC-002 | P0 | Assessment/leak-resistance docs | Docs audit | TODO |  |
| DOC-003 | P0 | Matching/category docs | Docs audit | TODO |  |
| DOC-004 | P0 | Validation procedure/results docs | Docs audit | TODO |  |
| DOC-005 | P0 | FSP integration scheme docs | Docs audit | TODO |  |
| DOC-006 | P0 | API description | OpenAPI/docs | VERIFIED | docs/API_GUIDELINES.md; backend/app/main.py; backend/tests/test_errors.py |
| DOC-007 | P0 | Libraries/components with versions | COMPONENTS.md | VERIFIED | docs/COMPONENTS.md; backend/requirements.lock; backend/uv.lock; frontend/package-lock.json; qa/package-lock.json; docker-compose.yml |
| DOC-008 | P0 | Step-by-step build/deploy/local run | Setup/deployment docs | VERIFIED | docs/DEPLOYMENT.md; .env.example; scripts/demo-reset.sh; .agent/runs/20261007-045717-c022/verification.log |
| DEMO-001 | P0 | Full candidate→assessment→employer→contact demo | Playwright + demo reset | TODO |  |
| BONUS-001 | P2 | Fake-vacancy / bad-employer protection concept/MVP | Trust design | TODO |  |
| BONUS-002 | P2 | ATS integration concept | Docs/contract | TODO |  |
| INNOV-001 | P2 | Verified Skill Passport | UI/domain | TODO |  |
| INNOV-002 | P2 | Evidence freshness | Domain/UI | TODO |  |
| INNOV-003 | P2 | Blind Discovery | Privacy/UI | TODO |  |
| INNOV-004 | P2 | Talent Radar | Employer UI | TODO |  |
| INNOV-005 | P2 | Assessment Integrity signals | Advisory telemetry, hidden-check and cross-submission similarity signals rendered in candidate result UI | IMPLEMENTED | backend/tests/test_assessments.py:43-145; backend/app/assessments.py; frontend/src/components/candidate-assessment.tsx; docs/AI_ASSESSMENT_INTEGRITY.md |
| INNOV-006 | P2 | Career Graph | Candidate UI | TODO |  |
| INNOV-007 | P2 | Validation Dashboard | Demo UI | TODO |  |
| INNOV-008 | P1 | Deterministic Jury Demo reset | Script/E2E | TODO |  |
