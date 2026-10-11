# Jury demo scenario

Public demo URL: the value of `APP_BASE_URL` in the deployment `.env`.

The live deployment uses Keycloak at `KEYCLOAK_PUBLIC_URL` and accepts only
`.ru` email addresses. Mailpit is used as the synthetic demo mailbox for email
verification; no real credentials or personal data belong in screenshots or
the repository.

Reset:
```bash
DEMO_RESET_CONFIRM=YES ./scripts/demo-reset.sh
```

The reset is a deterministic empty-database baseline, not a fixture containing
pre-authenticated people. The jury operator creates synthetic accounts through
Keycloak/Mailpit so no credentials or personal data are stored in the repository.

Primary scenario:
1. branded landing;
2. candidate registers/signs in with a `.ru` email through Keycloak and email verification;
3. consent/privacy; show that minor flow exists with synthetic private guardian-consent status, without exposing documents;
4. profile or PDF resume;
5. choose Backend/Middle declared grade;
6. start base assessment; show two demo candidates receive different concrete forms from the same calibrated blueprint;
7. demonstrate one progressive/session-specific task and explain anti-leak/anti-AI-by-design controls;
8. show system-scored result and verified category;
9. show a second candidate whose declared grade is **not confirmed** but remains discoverable with a clear marker;
10. link demo FSP ID; show synthetic verified achievements and a separate no-FSP candidate;
11. employer signs in;
12. employer creates hiring need with required/preferred skills;
13. Talent Radar shows relevant categories;
14. ProofMatch returns candidate ranking with evidence sources, confidence, FSP bounded contribution, gaps and explanation;
15. employer sends invitation with mandatory RUB salary;
16. prove contacts and chat are still locked;
17. candidate accepts → `MATCH_CREATED`;
18. show contact unlock and internal chat between matched parties. Chat is
    unlocked by the accepted match; completion of the later employer task is
    additional evidence and is not a prerequisite for opening the chat;
19. employer adds/uses an additional hiring stage/task and grades it; show that it creates employer-specific evidence without rewriting the global grade;
20. if local AI is enabled, request a draft employer task based on current need + approved historical tasks, then edit/approve it; if disabled, show deterministic/manual fallback;
21. optional vacancy/application scenario;
22. Validation Dashboard with actual matching and assessment metrics, including grade-discrimination/confusion data;
23. show actual load-test report for the CPU-only target profile;
24. Swagger/OpenAPI;
25. responsive desktop/tablet/mobile view.

Automate as much as practical with Playwright. Use only deterministic synthetic/demo users in screenshots/Telegram.

Current verification boundary: registration/email verification, public HTTPS,
health endpoints, brand/security smoke checks, assessment uniqueness and the
invitation/chat/employer-task backend slice are verified separately. A single
authenticated Playwright run covering every step above is still the remaining
`DEMO-001` item in the requirements matrix.
