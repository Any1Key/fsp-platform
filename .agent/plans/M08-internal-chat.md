# M08 — Internal post-match chat

## Scope

Implement one end-to-end internal chat slice after the existing reverse-recruitment
match transition. The slice covers CHAT-001 through CHAT-004 and preserves PRIV-001:
no conversation or message exists before `MATCH_CREATED`; only the two identities
stored on the match may read or write the conversation.

## Evidence and decisions

- `docs/CHAT_AND_MATCHING.md` requires persisted text messages, conversation list,
  unread/history, contact exchange, an abuse/report action, and server-side membership
  checks.
- `docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md` section “Match and chat” confirms
  that messaging and contact unlock start only after candidate acceptance.
- `docs/DATA_MODEL.md` already names conversation, members, messages, read state and
  moderation/report records; this plan adds the concrete migration and API contract.

## Implementation steps

1. Add the M08 migration for conversations, members, messages, read receipts,
   contact exchanges and abuse reports.
2. Add a chat service with match-bound conversation creation, membership checks,
   history/list/read/message/contact/report operations, and safe audit metadata.
3. Call conversation creation from the existing accepted-invitation transaction.
4. Add typed REST endpoints for both roles and a responsive shared chat component.
5. Add integration tests for pre-match denial, post-match exchange, unread/read
   state, outsider denial, contact exchange and report behavior.
6. Update chat/API/data-model documentation, the requirement matrix and backlog with
   `IMPLEMENTED` evidence only. Never mark `VERIFIED` or change readiness state.

## Verification

- Run the focused backend chat/invitation/migration tests.
- Run backend full tests and frontend typecheck/build.
- Inspect the diff for message-body logging, unauthorized access, and tracking status.
