# Match lifecycle and internal chat

## Match definition

Primary reverse-recruitment path:
`employer invitation → candidate views → candidate accepts → MATCH_CREATED`

Candidate-initiated vacancy applications produce the same matched state when
the vacancy owner accepts the application. The application status transition,
private invitation bridge, `talent_match`, conversation, and unlock events are
committed together, so an accepted application cannot expose chat without a
corresponding match.

## Before match

Before `MATCH_CREATED`:
- employer cannot send chat messages to candidate;
- candidate cannot send chat messages to employer;
- candidate contact fields remain protected;
- employer communicates only through the structured invitation/offer object.

This preserves the core reverse-recruitment mechanic and prevents cold-message spam.

## After match

After `MATCH_CREATED`:
- create/open a private conversation for the two authorized parties;
- allow text messages and read/unread state;
- allow exchange of contact details in chat;
- expose candidate contact fields according to the original contact-unlock rule;
- allow employer hiring-pipeline stages/tasks;
- keep full authorization server-side.

The current implementation creates the conversation and its two membership rows in
the same database transaction as invitation acceptance. A pending or declined
invitation therefore has no conversation to address. An authenticated account that
is not one of the two match identities receives the same `CONVERSATION_NOT_FOUND`
boundary for history, messages, contacts and reports.

## MVP chat scope

Required:
- persisted text messages;
- conversation list;
- unread count;
- timestamps;
- basic delivered/read state if practical;
- abuse/report action;
- no cross-conversation access.

Attachments, typing indicators and presence are optional and must not delay P0.

## REST contract

- `GET /api/v1/chat/conversations` lists only the caller's matched conversations and
  includes the participant label, last-message preview and unread count.
- `GET /api/v1/chat/conversations/{id}` returns up to 100 persisted messages and
  exchanged contacts for a member of that conversation.
- `POST /api/v1/chat/conversations/{id}/messages` persists a trimmed text body up to
  4,000 characters.
- `POST /api/v1/chat/conversations/{id}/read` writes per-message read receipts for
  unread messages addressed to the caller.
- `POST /api/v1/chat/conversations/{id}/contacts` exchanges one caller-owned contact
  value with the other member; a later submission updates that caller's value.
- `POST /api/v1/chat/conversations/{id}/reports` records a basic moderation report.

The report audit event stores only the conversation/report IDs and reason. It never
copies message bodies, contact values, tokens or document contents into audit details.
The API intentionally uses polling/history REST endpoints for this MVP; WebSocket
transport can be added behind the same authorization service later.

## Transport

FastAPI WebSocket is acceptable, with REST fallback/history endpoints. Simpler polling is acceptable only if WebSocket work threatens the core deadline.

## Privacy

Never send private chat content to Telegram agent reporting. Use synthetic/demo users for UI screenshots. Avoid logging full message bodies.
