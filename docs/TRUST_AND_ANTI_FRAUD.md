# Employer trust / anti-fraud MVP

The MVP is an evidence-and-reporting layer around reverse recruitment. It does
not make a hidden global employer score and does not block the core matching or
accepted-match flow.

## Signals

Low-cost MVP signals:
- verified email;
- corporate-domain email vs disposable/free domain;
- company website/domain consistency;
- company profile completeness;
- invitation rejection/report rate;
- repeated duplicate vacancy/offer patterns;
- unrealistic salary/description anomaly flag;
- account age and activity.

## Controls

- `GET /api/v1/employer/trust` returns the employer's explicit badge evidence,
  advisory signals, current 24-hour outbound count and limit.
- A candidate can report an addressed offer with
  `POST /api/v1/candidate/invitations/{invitation_id}/report`. The report is
  scoped to that candidate/invitation pair and is idempotent.
- Open rows in `employer_trust_report` are the reviewer queue. Reviewers and
  admins can list them and mark them `reviewed` or `closed` through the
  reviewer trust endpoints.
- Normal employers have a 20-invitation/24-hour limit. An open report or at
  least two independent high-risk heuristic signals changes the limit to 3.
  This is a throttle, not an accusation or grade/ranking feature.
- The only badge-bearing evidence is the explicitly verified Keycloak email.
  Corporate-domain, website, completeness, age, outcome, duplicate-offer and
  offer-language checks are all labeled `heuristic` in the API/UI.
- A single heuristic never blocks an invitation. Salary and offer validation,
  candidate privacy, blind discovery, and match/contact unlock rules remain
  unchanged.

Invitation responses include a safe `employer_trust` summary for the candidate;
it never includes the employer's identity email, report details, reviewer
notes, candidate contacts, protected attributes, documents, or tokens.

Audit records contain only report ID, invitation ID, reason, and reviewer
resolution status. They do not copy report details or chat/contact content.

Future:
- legal entity verification;
- domain DNS/email verification;
- moderation console;
- fraud model using confirmed labels.

Document what is heuristic vs actually verified.
