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
            f"SMTP credentials missing for signature {signature!r} (smtp_pwd_env did not resolve to a password)"
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

    def _normalize(value: str | list[str] | None) -> list[str]:
        """Return a flat list of individual addresses.

        Accepts a single address, a comma/semicolon-separated string, a list
        of strings (each possibly comma/semicolon-separated), or ``None``.
        """
        if value is None:
            return []
        raw_items: list[str] = [value] if isinstance(value, str) else list(value)
        result: list[str] = []
        for item in raw_items:
            if not item:
                continue
            for part in item.replace(";", ",").split(","):
                addr = part.strip()
                if addr:
                    result.append(addr)
        return result

    def _join(value: str | list[str] | None) -> str | None:
        lst = _normalize(value)
        return ", ".join(lst) if lst else None

    to_header = _join(to)
    cc_header = _join(cc)
    bcc_list = _normalize(bcc)

    sig_html = _read_signature(signature)

    # Precompute attachments once so we can reuse them for every outgoing mail
    # (relevant when we split bcc recipients into individual messages below).
    prepared_attachments: list[tuple[bytes, str, str, str]] = []
    for att in attachments:
        if isinstance(att, str):
            file_path = Path(att)
            if not file_path.exists():
                continue
            mime, _ = mimetypes.guess_type(str(file_path))
            mime = mime or "application/octet-stream"
            maintype, _, subtype = mime.partition("/")
            prepared_attachments.append((file_path.read_bytes(), maintype, subtype, file_path.name))
        else:
            filename, content, mime = att
            mime = mime or "application/octet-stream"
            maintype, _, subtype = mime.partition("/")
            prepared_attachments.append((content, maintype, subtype, filename))

    def _build_message(to_val: str | None, cc_val: str | None) -> EmailMessage:
        m = EmailMessage()
        m["From"] = smtp_cfg["email_from"]
        if to_val:
            m["To"] = to_val
        if cc_val:
            m["Cc"] = cc_val
        m["Subject"] = subject
        if html is not None:
            m.set_content(text or "")
            full_html = html + (f"<p>{sig_html}</p>" if sig_html else "")
            m.add_alternative(full_html, subtype="html")
        else:
            body = text or ""
            if sig_html:
                body += "\n\n" + sig_html
            m.set_content(body)
        for content, maintype, subtype, filename in prepared_attachments:
            m.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )
        return m

    # Build the list of outgoing messages.
    # Every bcc recipient gets their own mail with the address in the "To"
    # header (i.e. bcc is split into individual sends: 20 bcc -> 20 mails).
    messages: list[tuple[EmailMessage, str]] = []
    if bcc_list:
        if to_header and to_header not in bcc_list:
            messages.append((_build_message(to_header, cc_header), "main"))
        for addr in bcc_list:
            messages.append((_build_message(addr, cc_header), f"bcc:{addr}"))
    else:
        messages.append((_build_message(to_header, cc_header), "main"))

    port = int(smtp_cfg["smtp_port"])
    logger.info(
        "Sending email signature=%s host=%s port=%d user=%s pwd_len=%d to=%s cc=%s bcc_count=%d messages=%d subject=%s",
        signature,
        smtp_cfg["smtp"],
        port,
        smtp_user,
        len(pwd),
        to_header or "-",
        cc_header or "-",
        len(bcc_list),
        len(messages),
        subject,
    )
    tls_context = _build_tls_context()
    failures: list[tuple[str, BaseException]] = []
    for outgoing, label in messages:
        try:
            await aiosmtplib.send(
                outgoing,
                hostname=smtp_cfg["smtp"],
                port=port,
                username=smtp_user,
                password=pwd,
                use_tls=port == 465,
                start_tls=port == 587,
                tls_context=tls_context,
            )
        except Exception as exc:
            logger.exception("SMTP send failed (signature=%s, message=%s)", signature, label)
            failures.append((label, exc))

    if failures:
        summary = ", ".join(f"{label}: {exc}" for label, exc in failures)
        raise RuntimeError(
            f"SMTP send failed for {len(failures)}/{len(messages)} message(s) (signature={signature!r}): {summary}"
        )
