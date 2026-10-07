# Reverse-recruitment invitations

M07 implements the primary reverse-recruitment interaction:

`Talent Radar → employer invitation → candidate inbox → accept/decline → match`

## Offer contract

An employer can send an invitation without publishing a vacancy. The request contains:

- candidate profile ID from the employer's Talent Radar result;
- a positive `salary_min_rub` and `salary_max_rub`, with minimum no greater than maximum;
- a non-empty offer description.

The candidate must be discoverable, have publication consent, and have at least one
platform assessment with a confirmed grade. Candidates with an unconfirmed grade remain
searchable in Talent Radar, but the invitation endpoint rejects them until the grade is
confirmed.

The employer must first have a company name and public contact method. Both are snapshotted
onto the invitation so the candidate sees a stable company/contact offer even if the employer
later edits its profile. A pending duplicate invitation for the same employer and candidate is
rejected; declined or accepted invitations remain immutable and can be audited.

## API state and authorization

- `POST /api/v1/employer/invitations` creates an invitation.
- `GET /api/v1/employer/invitations` lists only invitations sent by the employer.
- `GET /api/v1/employer/invitations/{id}` reads only the employer's own invitation.
- `GET /api/v1/candidate/invitations` lists only invitations addressed to the candidate.
- `POST /api/v1/candidate/invitations/{id}/respond` accepts or declines only an addressed,
  pending invitation. Repeating the same action is idempotent; changing a terminal state is
  rejected.

Invitation responses contain the salary, offer, company and public contact method. They never
contain candidate email, phone, date of birth, documents, or other protected profile fields.

## Match transition

Acceptance updates the invitation and inserts one `talent_match` row in one transaction. The
same transaction writes `MATCH_CREATED` and `CONTACT_UNLOCKED` to `domain_event` and records
non-PII audit events. The timestamps are present on both the invitation and match state.
This is the server-side unlock boundary for M08 chat; no conversation or direct message exists
in this M07 slice.

Decline only changes the invitation to `declined` and does not create a match or unlock event.
