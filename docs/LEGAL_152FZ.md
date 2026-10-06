# 152-FZ-oriented privacy design

This is an engineering control set, not a legal opinion or certification of compliance. Final production wording/processes require legal review.

## Principles

- purpose limitation and data minimization;
- explicit versioned consent for processing/publication where required;
- least-privilege access and role separation;
- contact-data protection before match;
- audit of consent, access-sensitive transitions and data changes;
- configurable retention/deletion/anonymization workflows;
- secure transport and secret handling;
- avoid external transfer of personal data by default;
- production deployment/storage location must be reviewed for Russian data-localization requirements.

## Candidate controls

Provide:
- privacy/discoverability settings;
- consent version/timestamp/source;
- withdrawal of publication/discoverability consent;
- account/data deletion request workflow or demonstrable concept;
- profile export concept;
- clear separation of public professional profile and protected contacts/documents.

## Minor candidates

Date of birth/age is private and excluded from ranking. For a candidate below the configured adult threshold:
- require parent/legal-representative consent document status before publication/discoverability;
- store document in private protected storage;
- show only status to authorized candidate/admin flow, never employer;
- log upload/replacement/review events;
- support retention/deletion policy.

Exact document wording and legal threshold are configuration/legal-review items.

## Telegram/agent reporting

Agent Telegram reports must never contain real candidate PII, resume contents, chat contents, tokens or consent documents. Screenshots sent to Telegram must use deterministic synthetic demo users or a redacted demo mode.
