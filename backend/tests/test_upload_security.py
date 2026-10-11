from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.config import Settings
from app.upload_security import (
    private_storage_path,
    read_bounded_pdf,
    store_private_bytes,
)


def _upload(filename: str, body: bytes = b"%PDF-1.7\nsynthetic", content_type: str = "application/pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(body),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.parametrize(
    ("filename", "detail"),
    [
        ("resume\x00.pdf", "resume_invalid_filename"),
        ("resume\r\n.pdf", "resume_invalid_filename"),
        ("я" * 128 + ".pdf", "resume_invalid_filename"),
    ],
)
def test_pdf_upload_rejects_control_characters_and_oversized_utf8_names(filename, detail):
    with pytest.raises(HTTPException) as error:
        read_bounded_pdf(_upload(filename), max_bytes=1024, error_prefix="resume")

    assert error.value.status_code == 422
    assert error.value.detail == detail


def test_pdf_upload_normalizes_windows_path_metadata_without_using_it_as_storage_path():
    filename, content = read_bounded_pdf(
        _upload(r"..\candidate\resume-final.pdf"),
        max_bytes=1024,
        error_prefix="resume",
    )

    assert filename == "resume-final.pdf"
    assert content.startswith(b"%PDF-")


@pytest.mark.parametrize(
    ("body", "content_type", "max_bytes", "detail"),
    [
        (b"%PDF-1.7", "text/plain", 1024, "resume_invalid_type"),
        (b"not-pdf", "application/pdf", 1024, "resume_invalid_pdf"),
        (b"%PDF-1.7-too-large", "application/pdf", 8, "resume_too_large"),
    ],
)
def test_pdf_upload_requires_declared_pdf_type_signature_and_bound(body, content_type, max_bytes, detail):
    with pytest.raises(HTTPException) as error:
        read_bounded_pdf(
            _upload("resume.pdf", body, content_type),
            max_bytes=max_bytes,
            error_prefix="resume",
        )

    assert error.value.detail == detail


def test_private_storage_repairs_existing_root_and_creates_mode_600_file(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o755)
    settings = Settings(private_storage_dir=str(root))

    destination = store_private_bytes(settings, "document.pdf", b"private bytes")

    assert destination == root / "document.pdf"
    assert destination.read_bytes() == b"private bytes"
    assert root.stat().st_mode & 0o777 == 0o700
    assert destination.stat().st_mode & 0o777 == 0o600


def test_private_storage_refuses_traversal_and_existing_destination(tmp_path):
    settings = Settings(private_storage_dir=str(tmp_path / "private"))

    with pytest.raises(HTTPException) as traversal:
        private_storage_path(settings, "../outside.pdf")
    assert traversal.value.detail == "private_storage_invalid"

    store_private_bytes(settings, "document.pdf", b"first")
    with pytest.raises(FileExistsError):
        store_private_bytes(settings, "document.pdf", b"second")
    assert (tmp_path / "private" / "document.pdf").read_bytes() == b"first"


def test_private_storage_rejects_configured_root_symlink(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "private"
    root.symlink_to(target, target_is_directory=True)
    settings = Settings(private_storage_dir=str(root))

    with pytest.raises(HTTPException) as error:
        store_private_bytes(settings, "document.pdf", b"private bytes")

    assert error.value.detail == "private_storage_invalid"
    assert not (target / "document.pdf").exists()
