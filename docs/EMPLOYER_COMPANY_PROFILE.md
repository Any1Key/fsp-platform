# Employer company profile

`EMP-001` is implemented as the first M06 employer-discovery slice.

After employer role onboarding, the employer workspace calls:

- `GET /api/v1/employer/company`
- `PATCH /api/v1/employer/company`

The API derives ownership from the validated Keycloak subject. A first `GET`
creates an empty employer-owned record so the UI has a stable loading/empty
state. Saving requires a non-blank company name. The editable company-facing
fields are name, description, industry, HTTP/HTTPS website, city/region, and
an explicitly supplied public hiring contact method.

The response never includes the employer's Keycloak email or token. The public
contact field is not inferred from account identity: it is only returned after
the employer deliberately enters it. This profile is the source record for
future hiring needs, invitations, and Talent Radar presentation; those flows
remain separate M06/M07 work units.

Both endpoints require the `employer` role. Candidate tokens receive
`ROLE_REQUIRED`, and each employer can access only its own company row. Unknown
fields, blank/overlong values, unsafe website schemes, and saving without a
company name are rejected through the standard error envelope. Failed
validation does not update an existing profile.
