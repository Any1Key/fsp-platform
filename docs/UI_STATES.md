# UI data-surface states

FSP Talent uses four explicit presentation states for asynchronous evidence and discovery
surfaces:

- `loading` announces that data is being fetched and uses `aria-busy="true"` on the status
  element. It is not an empty result and must not imply that the candidate has no evidence.
- `empty` means the request succeeded but there is no record in the current scope. The copy
  explains the next useful action where one exists.
- `error` is a recoverable request or authorization failure. It uses an alert and offers retry
  on surfaces where retry is safe. It must not expose API error payloads or private data.
- `unconfirmed-grade` means a declared grade is visible but the platform assessment has not
  confirmed it. It is a warning label, never a ranking rejection or a replacement for the
  declared grade.

The shared React vocabulary lives in `frontend/src/components/ui-state.tsx`. Candidate Skill
Passport, employer Talent Radar, Validation Dashboard, and the authentication shell use the same
semantics while retaining domain-specific messages and actions.

These states do not alter API contracts, ProofMatch scoring, candidate visibility, contact unlock,
or privacy boundaries. The browser/source contract is `qa/tests/ui-states-contract.spec.ts`;
external supervision owns visual screenshot verification.
