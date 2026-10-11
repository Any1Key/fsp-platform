# Security and privacy

The project handles personal/employment data. Treat the 152-FZ requirement as a design obligation, without claiming formal legal compliance without legal review. See `LEGAL_152FZ.md`.

## Identity
- working Keycloak/OIDC demo;
- email verification;
- `.ru` email-domain restriction at registration/identity boundary;
- server-side JWT validation;
- server-side role authorization.

## Browser boundary

The API accepts only explicit HTTP(S) origins from `CORS_ALLOWED_ORIGINS`; the
configuration rejects wildcards, paths, credentials in the origin, and empty
origin lists. Bearer-token requests do not use ambient browser credentials, so
CORS credentials remain disabled. The preflight contract covers every REST
method used by the application, including `DELETE`, and exposes only the safe
`X-Request-ID` response header.

API responses, including errors and CORS preflight responses, set
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive
`Permissions-Policy` for camera, microphone, geolocation, and payment. The
API adds HSTS only when `APP_ENV=production`; local HTTP development is not
forced into an HTTPS policy. The Next.js frontend sends the same non-HSTS
browser policy. TLS termination and certificate management remain deployment
responsibilities.

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

Age/date of birth must never influence matching/ranking. The candidate-only
`/api/v1/candidate/protected-profile` boundary stores a nullable DOB, derives
minor state server-side, requires processing consent for writes, and excludes
the value from the professional profile, audit details and employer responses.
The age threshold is configuration, not client input. This does not replace
the separate legal-representative consent-document workflow.

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
The candidate privacy boundary is implemented by `GET/PATCH
/api/v1/candidate/privacy`. It persists processing/publication consent version,
timestamp and source, keeps discoverability separate, and records non-PII
`audit_event` rows for grants, withdrawals and discoverability changes. The
configured policy version is supplied by the server, not the browser.
Publication requires processing consent; discoverability requires publication
consent. Withdrawal cascades to dependent settings, so discoverability off
removes a candidate from future search.

`POST /api/v1/candidate/privacy/export` records an authenticated export request
as `requested` and creates a non-PII audit event. `GET
/api/v1/candidate/privacy/requests` exposes only the authenticated candidate's
request ledger, including status and the server-scheduled processing date.
Repeated active requests are idempotent. `POST
/api/v1/candidate/privacy/delete` queues deletion and immediately withdraws
processing/publication consent and discoverability; it does not run destructive
deletion inline. The configurable `PRIVACY_RETENTION_DAYS` window gives the
reviewed fulfillment worker time to apply retention and legal holds. Until that
worker and final legal policy are deployed, these endpoints are a demonstrable
MVP workflow rather than a claim of completed legal deletion.

For a configured minor threshold, publication/discoverability requires a
current submitted or approved legal-representative document. If a saved DOB
changes an already published profile into the minor state without a current
document, publication and discoverability are withdrawn. Employer never
receives the document.

## Minor documents
- private protected storage;
- candidate-only `GET/POST/DELETE /api/v1/candidate/minor-consent-document` boundary;
- validate PDF type/signature/size and store under a UUID key;
- return status and safe metadata, never file bytes or storage paths;
- authorization checks;
- audit upload/replace/review/delete without filenames, hashes, or raw content;
- replacement removes the superseded private artifact after the new row commits;
- candidate withdrawal marks the current row `withdrawn`, removes its private
  artifact, and withdraws minor publication/discoverability before commit;
- configurable retention;
- do not include in Telegram or logs.

## Secrets
Never commit DB passwords, Keycloak admin password, AI tokens, Telegram bot token or GitHub token.

## Logs
No passwords/tokens. Avoid raw resume/chat text. Mask contact data where possible. Use request IDs and safe metadata. The Python API installs the tested `SafeLogFilter` from `backend/app/logging_safety.py`; it redacts credentials in messages, logging arguments, exception tracebacks, stack text and sensitive query parameters. The API does not log request bodies. See `docs/SECURITY_QUERY_AUDIT.md` for the complete secret/log and query/index audit.

## Request rate limits

The API applies a bounded fixed-window limiter before request bodies and
dependencies are processed for abuse-sensitive operations:

- registration-domain checks: 10 per minute per connection peer;
- assessment creation/submission: 6 per hour per bearer-token fingerprint;
- candidate resume and minor-consent uploads: 5 per hour per bearer-token
  fingerprint;
- employer invitations: 30 per minute per bearer-token fingerprint, in
  addition to the employer-trust business limit;
- matched-chat messages: 60 per minute per bearer-token fingerprint;
- candidate privacy export/deletion requests: 5 per hour per bearer-token
  fingerprint.

Limited responses use the shared error envelope with `429 RATE_LIMITED`,
`Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and
`X-Request-ID` headers. Health checks, preflight, reads, and normal navigation
remain available. The limiter stores only short-lived counters keyed by a
one-way connection-peer or bearer-token fingerprint; it does not store tokens,
raw addresses, request bodies, or personal data. Forwarded headers are not
trusted by this boundary.

The default store is bounded and process-local. A multi-worker or multi-node
deployment must apply the same policy at a trusted ingress or use a shared
counter store before relying on cluster-wide quotas. Configuration is exposed
through `RATE_LIMIT_*` environment variables via the settings boundary, and
`RATE_LIMIT_ENABLED=false` is reserved for controlled local diagnostics.

## Uploads
Resume and minor-consent uploads are candidate-scoped and require processing
consent. Validate the PDF filename, MIME, signature and configured size before
writing. The shared upload boundary rejects filename control characters,
normalizes path separators for display metadata only, and enforces the UTF-8
filename byte limit. Use UUID storage keys below the configured private root;
the root is reasserted as mode `0700`, configured root symlinks are rejected,
and files are created exclusively without following a final symlink at mode
`0600`. Writes are flushed before the transaction is committed, and failures
remove the private artifact. Never return storage paths, hashes, raw bytes or
resume text from the upload API. Isolate the later parser and require review
before extracted fields become profile data. Failed writes must not leave a
database row or file.

## Assessment integrity telemetry
If focus/paste/timing events are collected, disclose the behavior, minimize the data, retain only what is necessary and use signals for review rather than automatic accusations.

## Telegram/agent reporting
Never send real candidate PII, resumes, chat text, minor documents or tokens to
Telegram. `agent/telegram.sh` enforces this boundary by mapping only known
supervisor events to fixed safe summaries, rejecting arbitrary messages,
restricting photos to PNG-signature files under `.agent/screenshots/latest`,
and disabling document uploads. UI screenshots sent by the autonomous agent
must use deterministic synthetic/demo accounts or redaction.

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
