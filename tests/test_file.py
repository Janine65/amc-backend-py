"""Tests for ``/files`` (upload + download)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def test_download_requires_auth(client: TestClient) -> None:
    assert client.get("/files/download", params={"filename": "x.pdf"}).status_code == 401


def test_download_unknown(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/files/download",
        params={"filename": "definitely-not-here.xlsx"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_upload_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/files/upload",
        files={"file": ("test.pdf", b"%PDF-", "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_invalid_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/files/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_upload_pdf(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/files/upload",
        files={"file": ("pytest_tmp.pdf", io.BytesIO(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["filename"] == "pytest_tmp.pdf"
