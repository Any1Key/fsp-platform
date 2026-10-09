"""Privacy-safe employer trust signals and invitation reports.

This module deliberately keeps trust explainable. Keycloak email verification
is the only badge-bearing signal; all other signals are advisory heuristics.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import Principal, sync_identity
from .companies import _ensure_company

TrustReportReason = Literal["fake_vacancy", "fee_request", "misleading_offer", "spam", "other"]
TrustReportStatus = Literal["open", "reviewed", "closed"]

NORMAL_INVITATION_LIMIT = 20
REVIEW_INVITATION_LIMIT = 3
INVITATION_WINDOW = timedelta(hours=24)
REPORT_REASONS = {"fake_vacancy", "fee_request", "misleading_offer", "spam", "other"}
REPORT_STATUSES = {"open", "reviewed", "closed"}
FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "mail.ru",
    "inbox.ru",
    "list.ru",
    "bk.ru",
    "yandex.ru",
    "ya.ru",
    "outlook.com",
    "hotmail.com",
}
ANOMALY_TERMS = {
    "pay a fee",
    "registration fee",
    "платный доступ",
    "оплатить обучение",
    "оплатить комиссию",
    "crypto transfer",
    "криптовалюта",
}


def _signal(
    key: str,
    label: str,
    category: Literal["verified", "heuristic"],
    signal_status: Literal["pass", "attention", "not_available"],
    explanation: str,
) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "category": category,
        "status": signal_status,
        "explanation": explanation,
    }


def _email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def _website_domain(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return host or None


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _offer_anomalies(salary_min_rub: int, salary_max_rub: int, description: str) -> list[str]:
    normalized = description.casefold()
    anomalies: list[str] = []
    if salary_max_rub > 5_000_000:
        anomalies.append("salary_outlier")
    if any(term in normalized for term in ANOMALY_TERMS):
        anomalies.append("payment_language")
    return anomalies


def _company_stats(db: Session, company_id: str, since: datetime) -> dict[str, int]:
    counts = (
        db.execute(
            text(
                "SELECT COUNT(*) AS invitations, "
                "SUM(CASE WHEN status <> 'pending' THEN 1 ELSE 0 END) AS responded, "
                "SUM(CASE WHEN status = 'declined' THEN 1 ELSE 0 END) AS declined "
                "FROM invitation WHERE company_id = :company_id AND created_at >= :since"
            ),
            {"company_id": company_id, "since": since},
        )
        .mappings()
        .one()
    )
    duplicate_groups = db.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "SELECT salary_min_rub, salary_max_rub, offer_description "
            "FROM invitation WHERE company_id = :company_id AND created_at >= :since "
            "GROUP BY salary_min_rub, salary_max_rub, offer_description HAVING COUNT(*) >= 2"
            ") duplicate_groups"
        ),
        {"company_id": company_id, "since": since},
    ).scalar_one()
    open_reports = db.execute(
        text(
            "SELECT COUNT(*) FROM employer_trust_report "
            "WHERE company_id = :company_id AND status = 'open'"
        ),
        {"company_id": company_id},
    ).scalar_one()
    return {
        "invitations": int(counts["invitations"] or 0),
        "responded": int(counts["responded"] or 0),
        "declined": int(counts["declined"] or 0),
        "duplicate_groups": int(duplicate_groups or 0),
        "open_reports": int(open_reports or 0),
    }


def _company_context(db: Session, company_id: str):
    return (
        db.execute(
            text(
                "SELECT c.id, c.name, c.description, c.industry, c.website, c.location, "
                "c.public_contact_method, ui.email, ui.email_verified, ui.created_at "
                "FROM company c JOIN user_identity ui ON ui.id = c.owner_identity_id "
                "WHERE c.id = :company_id"
            ),
            {"company_id": company_id},
        )
        .mappings()
        .one_or_none()
    )


def get_trust_profile(
    db: Session,
    company_id: str,
    *,
    offer: tuple[int, int, str] | None = None,
) -> dict[str, Any]:
    """Build a safe trust projection for an employer-owned company."""

    company = _company_context(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_not_found")

    now = datetime.now(UTC)
    since = now - INVITATION_WINDOW
    stats = _company_stats(db, company_id, since)
    email_domain = _email_domain(company["email"])
    website_domain = _website_domain(company["website"])
    heuristic_flags: list[str] = []
    signals: list[dict[str, str]] = []

    if company["email_verified"]:
        signals.append(
            _signal(
                "verified_email",
                "Подтвержденный email",
                "verified",
                "pass",
                "Email подтвержден через Keycloak; это единственный badge-bearing сигнал.",
            )
        )
    else:
        signals.append(
            _signal(
                "verified_email",
                "Подтвержденный email",
                "verified",
                "attention",
                "Email еще не подтвержден в identity provider.",
            )
        )

    if email_domain in FREE_EMAIL_DOMAINS:
        heuristic_flags.append("free_email_domain")
        signals.append(
            _signal(
                "corporate_email_domain",
                "Корпоративный домен",
                "heuristic",
                "attention",
                "Используется публичный почтовый домен; это не доказательство недобросовестности.",
            )
        )
    else:
        signals.append(
            _signal(
                "corporate_email_domain",
                "Корпоративный домен",
                "heuristic",
                "pass",
                "Email выглядит как адрес собственного домена; DNS или юридическая проверка не выполнялась.",
            )
        )

    if website_domain is None:
        signals.append(
            _signal(
                "website_consistency",
                "Сайт и email",
                "heuristic",
                "not_available",
                "Сайт компании не указан.",
            )
        )
    elif website_domain == email_domain or website_domain.endswith(f".{email_domain}"):
        signals.append(
            _signal(
                "website_consistency",
                "Сайт и email",
                "heuristic",
                "pass",
                "Домен сайта совпадает с доменом email; это эвристическая проверка.",
            )
        )
    else:
        heuristic_flags.append("website_mismatch")
        signals.append(
            _signal(
                "website_consistency",
                "Сайт и email",
                "heuristic",
                "attention",
                "Домен сайта отличается от email; нужна ручная проверка, автоматического вывода нет.",
            )
        )

    profile_fields = (
        company["name"],
        company["description"],
        company["website"],
        company["location"],
        company["public_contact_method"],
    )
    if all(field and str(field).strip() for field in profile_fields):
        signals.append(
            _signal(
                "profile_completeness",
                "Профиль компании",
                "heuristic",
                "pass",
                "Название, описание, сайт, локация и публичный контакт заполнены.",
            )
        )
    else:
        signals.append(
            _signal(
                "profile_completeness",
                "Профиль компании",
                "heuristic",
                "attention",
                "Профиль заполнен не полностью; это сигнал качества, а не обвинение.",
            )
        )

    account_age = now - _as_utc(company["created_at"])
    if account_age >= timedelta(days=30):
        signals.append(
            _signal(
                "account_age",
                "Возраст аккаунта",
                "heuristic",
                "pass",
                "Аккаунт существует не менее 30 дней.",
            )
        )
    else:
        signals.append(
            _signal(
                "account_age",
                "Возраст аккаунта",
                "heuristic",
                "attention",
                "Новый аккаунт; сам по себе этот сигнал не ограничивает найм.",
            )
        )

    if stats["responded"] >= 3 and stats["declined"] / stats["responded"] >= 0.66:
        heuristic_flags.append("rejection_rate")
        signals.append(
            _signal(
                "invitation_outcomes",
                "Ответы на приглашения",
                "heuristic",
                "attention",
                "Доля отклоненных приглашений за последние 24 часа высока; нужна проверка контекста.",
            )
        )
    else:
        signals.append(
            _signal(
                "invitation_outcomes",
                "Ответы на приглашения",
                "heuristic",
                "pass",
                "Нет достаточного сигнала по отклоненным приглашениям за последние 24 часа.",
            )
        )

    if stats["duplicate_groups"] > 0:
        heuristic_flags.append("duplicate_offers")
        signals.append(
            _signal(
                "duplicate_offers",
                "Повторяющиеся офферы",
                "heuristic",
                "attention",
                "Обнаружены одинаковые salary/offer пары; повтор может быть нормальным и требует проверки.",
            )
        )
    else:
        signals.append(
            _signal(
                "duplicate_offers",
                "Повторяющиеся офферы",
                "heuristic",
                "pass",
                "Повторяющиеся salary/offer пары не обнаружены.",
            )
        )

    if offer is not None:
        anomalies = _offer_anomalies(*offer)
        if anomalies:
            heuristic_flags.append("offer_anomaly")
            signals.append(
                _signal(
                    "offer_anomaly",
                    "Проверка оффера",
                    "heuristic",
                    "attention",
                    "В оффере есть формальные признаки, требующие ручной проверки; это не автоматический отказ.",
                )
            )

    review_state = stats["open_reports"] > 0 or len(set(heuristic_flags)) >= 2
    return {
        "company_id": company_id,
        "state": "review" if review_state else "normal",
        "badge": "verified_email" if company["email_verified"] else "none",
        "badge_label": "Verified email" if company["email_verified"] else "Email not verified",
        "review_queue": review_state,
        "open_report_count": stats["open_reports"],
        "outbound_used": stats["invitations"],
        "outbound_limit": REVIEW_INVITATION_LIMIT if review_state else NORMAL_INVITATION_LIMIT,
        "signals": signals,
        "review_reasons": sorted(set(heuristic_flags))
        + (["open_report"] if stats["open_reports"] > 0 else []),
    }


def public_trust_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """Remove employer-only moderation counters from candidate payloads."""

    return {
        "state": profile["state"],
        "badge": profile["badge"],
        "badge_label": profile["badge_label"],
        "signals": profile["signals"],
    }


def get_employer_trust(db: Session, principal: Principal) -> dict[str, Any]:
    _, company_id = _ensure_company(db, principal)
    return get_trust_profile(db, company_id)


def enforce_invitation_limit(
    db: Session,
    company_id: str,
    *,
    offer: tuple[int, int, str] | None = None,
) -> None:
    profile = get_trust_profile(db, company_id, offer=offer)
    if profile["outbound_used"] >= profile["outbound_limit"]:
        raise HTTPException(status_code=429, detail="employer_invitation_rate_limited")


def create_trust_report(
    db: Session,
    principal: Principal,
    invitation_id: str,
    *,
    reason: TrustReportReason,
    details: str | None,
) -> dict[str, Any]:
    if reason not in REPORT_REASONS:
        raise HTTPException(status_code=422, detail="employer_trust_report_reason_invalid")
    identity = sync_identity(db, principal)
    profile_id = db.execute(
        text("SELECT id FROM candidate_profile WHERE identity_id = :identity_id"),
        {"identity_id": identity["id"]},
    ).scalar_one_or_none()
    row = (
        db.execute(
            text(
                "SELECT id, company_id FROM invitation "
                "WHERE id = :invitation_id AND candidate_profile_id = :profile_id"
            ),
            {"invitation_id": invitation_id, "profile_id": profile_id or ""},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="invitation_not_found")

    existing = (
        db.execute(
            text(
                "SELECT id, status FROM employer_trust_report "
                "WHERE invitation_id = :invitation_id AND reporter_identity_id = :identity_id"
            ),
            {"invitation_id": invitation_id, "identity_id": identity["id"]},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        return {"id": existing["id"], "status": existing["status"]}

    report_id = str(uuid4())
    db.execute(
        text(
            "INSERT INTO employer_trust_report "
            "(id, invitation_id, company_id, reporter_identity_id, reason, details) "
            "VALUES (:id, :invitation_id, :company_id, :identity_id, :reason, :details)"
        ),
        {
            "id": report_id,
            "invitation_id": invitation_id,
            "company_id": row["company_id"],
            "identity_id": identity["id"],
            "reason": reason,
            "details": details.strip() if details and details.strip() else None,
        },
    )
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :identity_id, 'employer_trust_reported', :details)"
        ),
        {
            "id": str(uuid4()),
            "identity_id": identity["id"],
            "details": json.dumps(
                {"report_id": report_id, "invitation_id": invitation_id, "reason": reason},
                separators=(",", ":"),
            ),
        },
    )
    db.commit()
    return {"id": report_id, "status": "open"}


def list_trust_reports(
    db: Session,
    principal: Principal,
    *,
    report_status: TrustReportStatus,
) -> list[dict[str, Any]]:
    if report_status not in REPORT_STATUSES:
        raise HTTPException(status_code=422, detail="employer_trust_report_status_invalid")
    identity = sync_identity(db, principal)
    del identity
    rows = (
        db.execute(
            text(
                "SELECT r.id, r.invitation_id, r.company_id, c.name AS company_name, r.reason, "
                "r.details, r.status, r.created_at, r.updated_at "
                "FROM employer_trust_report r JOIN company c ON c.id = r.company_id "
                "WHERE r.status = :status ORDER BY r.created_at ASC, r.id ASC"
            ),
            {"status": report_status},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def resolve_trust_report(
    db: Session,
    principal: Principal,
    report_id: str,
    *,
    report_status: Literal["reviewed", "closed"],
) -> dict[str, Any]:
    identity = sync_identity(db, principal)
    if report_status not in {"reviewed", "closed"}:
        raise HTTPException(status_code=422, detail="employer_trust_report_status_invalid")
    exists = db.execute(
        text("SELECT id FROM employer_trust_report WHERE id = :report_id"),
        {"report_id": report_id},
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="employer_trust_report_not_found")
    db.execute(
        text(
            "UPDATE employer_trust_report SET status = :status, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :report_id"
        ),
        {"status": report_status, "report_id": report_id},
    )
    db.execute(
        text(
            "INSERT INTO audit_event (id, actor_identity_id, event_type, details) "
            "VALUES (:id, :identity_id, 'employer_trust_report_resolved', :details)"
        ),
        {
            "id": str(uuid4()),
            "identity_id": identity["id"],
            "details": json.dumps(
                {"report_id": report_id, "status": report_status}, separators=(",", ":")
            ),
        },
    )
    db.commit()
    row = (
        db.execute(
            text(
                "SELECT id, invitation_id, company_id, reason, details, status, created_at, updated_at "
                "FROM employer_trust_report WHERE id = :report_id"
            ),
            {"report_id": report_id},
        )
        .mappings()
        .one()
    )
    return dict(row)
