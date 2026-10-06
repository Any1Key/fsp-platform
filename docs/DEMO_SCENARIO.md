# Jury demo scenario

Reset:
```bash
./scripts/demo-reset.sh
```

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
18. show contact unlock and internal chat between matched parties;
19. employer adds/uses an additional hiring stage/task and grades it; show that it creates employer-specific evidence without rewriting the global grade;
20. if local AI is enabled, request a draft employer task based on current need + approved historical tasks, then edit/approve it; if disabled, show deterministic/manual fallback;
21. optional vacancy/application scenario;
22. Validation Dashboard with actual matching and assessment metrics, including grade-discrimination/confusion data;
23. show actual load-test report for the CPU-only target profile;
24. Swagger/OpenAPI;
25. responsive desktop/tablet/mobile view.

Automate as much as practical with Playwright. Use only deterministic synthetic/demo users in screenshots/Telegram.
