# Release acceptance criteria

Final `READY` requires:
- all P0 requirement rows `VERIFIED`;
- all P1 project-target rows `VERIFIED` or explicitly waived by owner with reason;
- no unresolved P0/P1 defects;
- clean build from repository;
- Docker services healthy on CPU-only host profile;
- empty-database migrations succeed;
- deterministic seed/demo reset succeeds;
- backend tests pass;
- frontend type/build checks pass;
- Playwright core E2E passes;
- responsive screenshot suite passes;
- authorization/contact/chat privacy tests pass;
- `.ru` registration restriction passes positive/negative tests;
- working Keycloak login/email verification/role/JWT demo passes;
- assessment forms are non-identical across test candidates while blueprint difficulty remains comparable;
- synthetic assessment validation shows non-degenerate grade discrimination without forced quotas;
- unconfirmed-grade candidate remains discoverable and clearly marked;
- employer hiring pipeline/task authoring/grading passes;
- local AI disabled fallback passes; optional AI-on flow passes if configured;
- FSP synthetic achievements display and bounded ranking contribution pass;
- minor consent-document flow and privacy authorization pass;
- internal chat is impossible before match and works after match;
- OpenAPI audit passes;
- 152-FZ-oriented engineering controls/docs audit passes;
- Telegram reporting contains no real PII/chat/minor documents;
- reproducible target load test completes and actual metrics are recorded;
- documentation audit passes;
- actual validation results exist;
- no committed secrets.

P2 must never destabilize P0/P1.

Final evidence should contain verification log, compose state, tests, OpenAPI, assessment/matching validation output, load-test report, representative responsive screenshots and final requirement-matrix snapshot.
