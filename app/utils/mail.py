"""SMTP / email helpers (port of ``AdressenService.sendEmail``)."""

from __future__ import annotations

import mimetypes
import os
import ssl
from collections.abc import Iterable
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
import certifi

from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger(__name__)

SIGNATURE_HTML_DIR = Path(__file__).resolve().parent.parent / "public" / "assets"


def _build_tls_context() -> ssl.SSLContext:
    """SSL context using certifi's CA bundle (fixes macOS "unable to get local issuer")."""
    return ssl.create_default_context(cafile=certifi.where())


def _read_signature(signature: str) -> str:
    path = SIGNATURE_HTML_DIR / f"{signature}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


async def send_mail(
    *,
    sender_signature: str | None = None,
    to: str | list[str] | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    subject: str,
    text: str = "",
    html: str | None = None,
    attachments: Iterable[str | tuple[str, bytes, str | None]] = (),
) -> None:
    """Send an email using the SMTP signature ``sender_signature``."""
    cfg = get_config()
    default_email = cfg.raw.get("defaultEmail") if cfg.raw else None
    signature = sender_signature or default_email or "JanineFranken"
    smtp_cfg = (cfg.raw or {}).get(signature)
    if not isinstance(smtp_cfg, dict):
        raise RuntimeError(f"SMTP signature {signature!r} is missing in config.json")

    # config.py resolves ${VAR} / bare ENV names in smtp_pwd_env already, so the
    # value here is the actual password. As fallback (for legacy configs that
    # only contain the env-var name without ENV resolution) we still try to look
    # it up in os.environ if the literal value happens to match an env name.
    pwd_raw = str(smtp_cfg.get("smtp_pwd_env", ""))
    pwd = (os.environ.get(pwd_raw, "") or pwd_raw).strip()
    smtp_user = str(smtp_cfg.get("smtp_user", "")).strip()
    if not smtp_user or not pwd:
        raise RuntimeError(
            f"SMTP credentials missing for signature {signature!r} "
            f"(smtp_pwd_env did not resolve to a password)"
        )
    try:
        smtp_user.encode("ascii")
        pwd.encode("ascii")
    except UnicodeEncodeError as exc:
        logger.warning(
            "SMTP credentials contain non-ASCII characters (signature=%s): %s",
            signature,
            exc,
        )

    def _join(value: str | list[str] | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            value = [v for v in value if v]
            return ", ".join(value) if value else None
        return value or None

    msg = EmailMessage()
    msg["From"] = smtp_cfg["email_from"]
    if to_h := _join(to):
        msg["To"] = to_h
    if cc_h := _join(cc):
        msg["Cc"] = cc_h
    if bcc_h := _join(bcc):
        msg["Bcc"] = bcc_h
    msg["Subject"] = subject

    sig_html = _read_signature(signature)
    if html is not None:
        msg.set_content(text or "")
        full_html = html + (f"<p>{sig_html}</p>" if sig_html else "")
        msg.add_alternative(full_html, subtype="html")
    else:
        body = text or ""
        if sig_html:
            body += "\n\n" + sig_html
        msg.set_content(body)

    for att in attachments:
        if isinstance(att, str):
            file_path = Path(att)
            if not file_path.exists():
                continue
            mime, _ = mimetypes.guess_type(str(file_path))
            mime = mime or "application/octet-stream"
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                file_path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=file_path.name,
            )
        else:
            filename, content, mime = att
            mime = mime or "application/octet-stream"
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

    port = int(smtp_cfg["smtp_port"])
    logger.info(
        "Sending email signature=%s host=%s port=%d user=%s pwd_len=%d "
        "to=%s cc=%s bcc=%s subject=%s",
        signature,
        smtp_cfg["smtp"],
        port,
        smtp_user,
        len(pwd),
        _join(to) or "-",
        _join(cc) or "-",
        _join(bcc) or "-",
        subject,
    )
    tls_context = _build_tls_context()
    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_cfg["smtp"],
            port=port,
            username=smtp_user,
            password=pwd,
            use_tls=port == 465,
            start_tls=port == 587,
            tls_context=tls_context,
        )
    except Exception:
        logger.exception("SMTP send failed (signature=%s)", signature)
        raise
