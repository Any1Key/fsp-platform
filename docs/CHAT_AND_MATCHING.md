# Match lifecycle and internal chat

## Match definition

Primary reverse-recruitment path:
`employer invitation → candidate views → candidate accepts → MATCH_CREATED`

Candidate-initiated vacancy applications may produce the same matched state when the employer accepts the application.

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

## Transport

FastAPI WebSocket is acceptable, with REST fallback/history endpoints. Simpler polling is acceptable only if WebSocket work threatens the core deadline.

## Privacy

Never send private chat content to Telegram agent reporting. Use synthetic/demo users for UI screenshots. Avoid logging full message bodies.
