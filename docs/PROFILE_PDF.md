# Standardized candidate profile PDF

The candidate can download a current, standardized profile artifact from the
profile panel or:

```text
GET /api/v1/candidate/profile/pdf
Authorization: Bearer <candidate-token>
```

The response is an on-demand `application/pdf` attachment named
`fsp-standardized-profile.pdf`. The server does not persist a generated copy.
It renders the same candidate-owned professional fields returned by the
profile API:

- display name, headline and location;
- summary and skills;
- structured experience and technologies;
- work preferences when supplied.

The first page identifies the artifact as candidate-declared information. It
does not claim an assessment result, verified grade or employer recommendation.
Protected account data is deliberately excluded: email, date of birth/minor
state, consent metadata, resume bytes/storage details, assessment data and
private contact information. The endpoint uses the existing candidate role and
self-scoped profile boundary; employers and other candidates cannot retrieve
the artifact.

The PDF is generated with a small deterministic CPU-only renderer. Text is
encoded safely in the PDF content stream, long content wraps, and additional
pages are added as needed. A blank profile still produces a valid standardized
artifact so the candidate can download it before completing every field.

Evidence: `backend/tests/test_candidate_profile.py` validates the PDF header,
download contract, extracted professional content, omission of protected data,
empty-profile behavior and candidate/employer scope.
