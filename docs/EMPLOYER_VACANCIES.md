# Employer vacancies

The first M11 slice gives an employer a company-scoped vacancy lifecycle:

- `GET /api/v1/employer/vacancies` lists owned vacancies;
- `POST /api/v1/employer/vacancies` creates a draft;
- `GET/PATCH /api/v1/employer/vacancies/{id}` reads or edits an owned vacancy;
- `POST /api/v1/employer/vacancies/{id}/publish` makes the draft published;
- `DELETE /api/v1/employer/vacancies/{id}` closes the vacancy without removing
  its history.

Every create and update request requires a positive `salary_min_rub` and
`salary_max_rub` range where the minimum is no greater than the maximum. The
server applies this rule even if a client skips browser validation and returns
`VACANCY_SALARY_INVALID` for an invalid range.

The vacancy currently stores title, description, optional location/work mode/
employment type, optional taxonomy specialization and grade, salary, status,
and lifecycle timestamps. Published rows are intentionally not exposed through
a candidate route in this slice; candidate browse and application handling are
the next M11 work units.

Vacancies are scoped through the authenticated employer's company. A different
employer receives the same not-found boundary for an item it does not own, and
a candidate cannot use employer vacancy routes. Close is a soft lifecycle
transition so future application and status-history records can refer to the
same vacancy.
