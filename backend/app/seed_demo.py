"""Validate the deterministic, privacy-safe demo baseline.

Keycloak owns demo identities and email verification, so this command must not
insert users, passwords, tokens, chat, or candidate documents. The Compose
reset has already applied migrations; this check proves the stable public
taxonomy needed by onboarding is present.
"""

from sqlalchemy import text

from .db import SessionFactory

EXPECTED_SPECIALIZATIONS = {
    "backend-engineering", "frontend-engineering", "full-stack-engineering",
    "qa-test-automation", "devops-sre", "data-engineering", "data-science-ml",
    "mobile-engineering",
}
EXPECTED_GRADES = {"junior", "middle", "senior"}


def main() -> None:
    with SessionFactory() as session:
        specializations = {
            row[0] for row in session.execute(
                text("SELECT slug FROM specialization WHERE active = true")
            )
        }
        grades = {row[0] for row in session.execute(text("SELECT slug FROM grade"))}

    missing_specializations = EXPECTED_SPECIALIZATIONS - specializations
    missing_grades = EXPECTED_GRADES - grades
    if missing_specializations or missing_grades:
        raise SystemExit(
            "demo baseline is incomplete: "
            f"specializations={sorted(missing_specializations)} "
            f"grades={sorted(missing_grades)}"
        )

    print(
        "demo baseline ready: migrations and deterministic taxonomy verified; "
        "Keycloak users and authenticated journey data are created during the jury flow"
    )

if __name__ == "__main__":
    main()
