"""Keycloak/OIDC authentication and local identity boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings, get_settings


class Role(StrEnum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"
    REVIEWER = "reviewer"


PUBLIC_ROLES = {Role.CANDIDATE, Role.EMPLOYER}
ALL_ROLES = {role.value for role in Role}


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any:
        """Return a PyJWT signing-key wrapper for a token."""


@dataclass(frozen=True)
class Principal:
    """The minimal, validated identity extracted from a Keycloak token."""

    subject: str
    email: str
    email_verified: bool
    role: Role


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_allowed_registration_email(email: str) -> bool:
    """Return whether an address has a real domain ending exactly in `.ru`."""

    normalized = normalize_email(email)
    if normalized.count("@") != 1 or any(character.isspace() for character in normalized):
        return False
    local_part, domain = normalized.rsplit("@", 1)
    return bool(local_part and domain and domain.endswith(".ru") and domain != ".ru")


def _claim_roles(claims: dict[str, Any], client_id: str) -> set[str]:
    roles: set[str] = set()
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict) and isinstance(realm_access.get("roles"), list):
        roles.update(role for role in realm_access["roles"] if isinstance(role, str))

    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        client_access = resource_access.get(client_id)
        if isinstance(client_access, dict) and isinstance(client_access.get("roles"), list):
            roles.update(role for role in client_access["roles"] if isinstance(role, str))
    return roles


class OIDCVerifier:
    """Validate Keycloak access tokens without persisting token material."""

    def __init__(self, settings: Settings, jwks_client: SigningKeyClient | None = None):
        self.settings = settings
        self._jwks_client = jwks_client or PyJWKClient(
            settings.keycloak_jwks_url,
            cache_jwk_set=True,
            lifespan=settings.keycloak_jwks_cache_seconds,
        )

    def verify(self, token: str) -> Principal:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.keycloak_client_id,
                issuer=self.settings.keycloak_issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_access_token") from exc

        subject = claims.get("sub")
        email = claims.get("email")
        email_verified = claims.get("email_verified") is True
        if not isinstance(subject, str) or not subject or not isinstance(email, str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_access_token")
        if self.settings.require_verified_email and not email_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")

        normalized_email = normalize_email(email)
        if not is_allowed_registration_email(normalized_email):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="registration_domain_not_allowed")

        roles = _claim_roles(claims, self.settings.keycloak_client_id)
        supported_roles = roles & ALL_ROLES
        if len(supported_roles) != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unsupported_or_ambiguous_role")
        return Principal(
            subject=subject,
            email=normalized_email,
            email_verified=email_verified,
            role=Role(next(iter(supported_roles))),
        )


def sync_identity(db: Session, principal: Principal) -> dict[str, Any]:
    """Provision or refresh the local identity from validated Keycloak claims."""

    existing = db.execute(
        text(
            "SELECT id, keycloak_sub, email, role, email_verified "
            "FROM user_identity WHERE keycloak_sub = :subject"
        ),
        {"subject": principal.subject},
    ).mappings().one_or_none()
    email_owner = db.execute(
        text("SELECT id, keycloak_sub FROM user_identity WHERE email = :email"),
        {"email": principal.email},
    ).mappings().one_or_none()
    if email_owner and email_owner["keycloak_sub"] != principal.subject:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="identity_email_conflict")

    if existing:
        db.execute(
            text(
                "UPDATE user_identity SET email = :email, role = :role, "
                "email_verified = :email_verified, updated_at = CURRENT_TIMESTAMP "
                "WHERE keycloak_sub = :subject"
            ),
            {
                "email": principal.email,
                "role": principal.role.value,
                "email_verified": principal.email_verified,
                "subject": principal.subject,
            },
        )
        db.commit()
        identity_id = existing["id"]
    else:
        identity_id = str(uuid4())
        try:
            db.execute(
                text(
                    "INSERT INTO user_identity "
                    "(id, keycloak_sub, email, role, email_verified) "
                    "VALUES (:id, :subject, :email, :role, :email_verified)"
                ),
                {
                    "id": identity_id,
                    "subject": principal.subject,
                    "email": principal.email,
                    "role": principal.role.value,
                    "email_verified": principal.email_verified,
                },
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="identity_already_exists") from exc

    return {
        "id": identity_id,
        "keycloak_sub": principal.subject,
        "email": principal.email,
        "role": principal.role.value,
        "email_verified": principal.email_verified,
    }


def require_role(*required_roles: Role):
    """Build a FastAPI dependency for a server-side role boundary."""

    def dependency(principal: Principal) -> Principal:
        if principal.role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role_required")
        return principal

    return dependency


def build_verifier(settings: Settings | None = None) -> OIDCVerifier:
    return OIDCVerifier(settings or get_settings())
