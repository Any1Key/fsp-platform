"""Shared security boundary for candidate-owned private PDF uploads."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import Settings

ALLOWED_CONTENT_TYPE = "application/pdf"


def read_bounded_pdf(
    upload: UploadFile,
    *,
    max_bytes: int,
    error_prefix: str,
) -> tuple[str, bytes]:
    """Validate upload metadata and read at most the configured PDF limit.

    The filename is display metadata only. It is never used as a storage path;
    path separators are stripped and control characters are rejected. The
    declared media type and PDF magic bytes are both required before a caller
    can persist the content.
    """

    filename = (upload.filename or "").strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in filename):
        raise HTTPException(status_code=422, detail=f"{error_prefix}_invalid_filename")

    normalized = unicodedata.normalize("NFC", filename.replace("\\", "/"))
    safe_filename = Path(normalized).name
    if (
        not safe_filename
        or safe_filename in {".", ".."}
        or len(safe_filename.encode("utf-8")) > 255
        or not safe_filename.lower().endswith(".pdf")
    ):
        raise HTTPException(status_code=422, detail=f"{error_prefix}_invalid_filename")
    if upload.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(status_code=422, detail=f"{error_prefix}_invalid_type")

    content = upload.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=422, detail=f"{error_prefix}_too_large")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail=f"{error_prefix}_invalid_pdf")
    return safe_filename, content


def private_storage_path(settings: Settings, storage_key: str) -> Path:
    """Return a private-root child while rejecting traversal and root symlinks."""

    if (
        not storage_key
        or storage_key in {".", ".."}
        or "/" in storage_key
        or "\\" in storage_key
    ):
        raise HTTPException(status_code=500, detail="private_storage_invalid")

    configured_root = Path(settings.private_storage_dir)
    if configured_root.is_symlink():
        raise HTTPException(status_code=500, detail="private_storage_invalid")
    try:
        configured_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not configured_root.is_dir():
            raise HTTPException(status_code=500, detail="private_storage_invalid")
        # mkdir's mode is ignored for an existing directory. Re-assert the
        # private boundary on every upload request.
        os.chmod(configured_root, 0o700)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="private_storage_unavailable") from exc

    root = configured_root.resolve()
    destination = (root / storage_key).resolve()
    if destination.parent != root:
        raise HTTPException(status_code=500, detail="private_storage_invalid")
    return destination


def store_private_bytes(settings: Settings, storage_key: str, content: bytes) -> Path:
    """Atomically create a mode-0600 private file without following symlinks."""

    destination = private_storage_path(settings, storage_key)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = os.open(destination, flags, 0o600)
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "wb", closefd=True) as stored:
            stored.write(content)
            stored.flush()
            os.fsync(stored.fileno())
    except (OSError, TypeError, ValueError):
        # The caller also performs transaction cleanup; this covers failures
        # before it receives the destination path.
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            destination.unlink(missing_ok=True)
        finally:
            raise
    return destination


def remove_private_file(settings: Settings, storage_key: str) -> None:
    """Best-effort cleanup for a file created during a failed transaction."""

    destination = private_storage_path(settings, storage_key)
    destination.unlink(missing_ok=True)
