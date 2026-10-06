# Security and privacy

The project handles personal/employment data. Treat the 152-FZ requirement as a design obligation, without claiming formal legal compliance without legal review. See `LEGAL_152FZ.md`.

## Identity
- working Keycloak/OIDC demo;
- email verification;
- `.ru` email-domain restriction at registration/identity boundary;
- server-side JWT validation;
- server-side role authorization.

The backend identity boundary validates issuer, audience, RS256 signature,
expiry, required claims, verified email and the candidate/employer role before
creating or refreshing a local `user_identity`. Tokens and passwords are never
persisted or written to logs. Candidate and employer context routes exercise
the role checks server-side; a valid token for one role cannot access the other
role's context.

Verified accounts that have no application role claim enter a pending state.
They can call only the role-onboarding endpoint, which accepts exactly one
candidate/employer choice and binds it to the validated Keycloak subject.
Repeated selection of the same role is idempotent; switching roles is rejected.
The persisted role is used for later no-role tokens, and an explicit conflicting
role claim is rejected. This permits the public Keycloak registration flow to
finish without granting an unselected account either protected workspace.

Keycloak owns registration, passwords, verification tokens and the verified
email state. Mailpit is a local/demo SMTP sink only. The Compose QA profile
proves that a new synthetic `.ru` account is unverified before the Mailpit link
is consumed and verified afterward; the QA admin password is injected from the
environment and is not logged or committed.

## Data minimization
Separate employer-visible professional profile from protected contacts, date of birth/minor status, consent documents and private interaction data.

Age/date of birth must never influence matching/ranking.

## Contact/chat privacy
Before a match:
- employer cannot see protected candidate contacts;
- employer and candidate cannot chat.

After valid match/unlock:
- only the matched parties can access the conversation;
- contact access follows the product state machine;
- authorization is enforced server-side.

Dedicated integration tests are mandatory.

## Consent
Persist processing/publication consent version + timestamp + purpose/source. Discoverability off removes candidate from future search.

For a configured minor threshold, publication/discoverability requires required legal-representative document status. Employer never receives the document.

## Minor documents
- private protected storage;
- validate file type/size;
- authorization checks;
- audit upload/replace/review/delete;
- configurable retention;
- do not include in Telegram or logs.

## Secrets
Never commit DB passwords, Keycloak admin password, AI tokens, Telegram bot token or GitHub token.

## Logs
No passwords/tokens. Avoid raw resume/chat text. Mask contact data where possible. Use request IDs and safe metadata.

## Uploads
Validate PDF/document signature/MIME, size, page count and filename. Isolate parsing.

## Assessment integrity telemetry
If focus/paste/timing events are collected, disclose the behavior, minimize the data, retain only what is necessary and use signals for review rather than automatic accusations.

## Telegram/agent reporting
Never send real candidate PII, resumes, chat text, minor documents or tokens to Telegram. UI screenshots sent by the autonomous agent must use deterministic synthetic/demo accounts or redaction.

## Authorization tests

`backend/tests/test_auth.py` covers the signed-token boundary, invalid or
expired tokens, issuer/audience checks, verified email, exact `.ru` policy,
identity provisioning, ambiguous roles and cross-role access. The tests use a
generated in-memory RSA key and do not require real Keycloak credentials.

At minimum:
- candidate A cannot read candidate B private data;
- employer cannot see contacts before unlock;
- no chat before match;
- matched outsider cannot read another conversation;
- candidate cannot use employer-only actions;
- employer cannot mutate platform assessment grade;
- employer can grade only own employer-authored stages;
- invitation belongs to correct parties;
- contact/chat unlock only through allowed transition;
- minor consent document inaccessible to employer;
- age absent from matching inputs.

## Agent/host
Codex stays in workspace-write mode. Host-level Docker verification is executed by supervisor scripts outside Codex.
Do not run the agent as NAS root/admin. Do not mount Docker socket, `/`, `/volume1`, SSH keys or secret directories into app containers.
