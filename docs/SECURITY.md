# Security and privacy

The project handles personal/employment data. Treat the 152-FZ requirement as a design obligation, without claiming formal legal compliance without legal review. See `LEGAL_152FZ.md`.

## Identity
- working Keycloak/OIDC demo;
- email verification;
- `.ru` email-domain restriction at registration/identity boundary;
- server-side JWT validation;
- server-side role authorization.

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
