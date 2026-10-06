# Employer trust / anti-fraud concept

Target bonus functionality must not block core MVP.

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

- candidate can report invitation/employer;
- rate limit bulk invitations;
- trust badge only from explicit verified evidence;
- suspicious state lowers outbound limits and enters review queue;
- never auto-accuse based on one heuristic.

Future:
- legal entity verification;
- domain DNS/email verification;
- moderation console;
- fraud model using confirmed labels.

Document what is heuristic vs actually verified.
