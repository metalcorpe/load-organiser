"""Mail adapters for the identity use cases. Wired at the composition root."""

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FileOutboxMailer:
    """Local/test sink: one JSON file per message. Not proof of real delivery."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def send(self, *, to: str, subject: str, text: str) -> None:
        name = f"{datetime.now(UTC):%Y%m%dT%H%M%S%f}-{uuid.uuid4().hex}.json"
        path = self._dir / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"to": to, "subject": subject, "text": text}, handle)


class SmtpMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        use_tls: bool,
        use_ssl: bool,
        user: str | None,
        password: str | None,
        from_email: str,
        from_name: str | None,
    ) -> None:
        self._smtp: dict[str, object] = {"host": host, "port": port}
        if use_tls:
            self._smtp["tls"] = True
        elif use_ssl:
            self._smtp["ssl"] = True
        if user:
            self._smtp["user"] = user
        if password:
            self._smtp["password"] = password
        self._from = (from_name, from_email)

    def send(self, *, to: str, subject: str, text: str) -> None:
        from emails.message import Message

        response = Message(subject=subject, text=text, mail_from=self._from).send(
            to=to, smtp=self._smtp
        )
        if response is None or response.status_code not in (250, 251):
            # Never log the recipient, body or link.
            logger.warning(
                "Identity mail not accepted by SMTP (status %s)",
                getattr(response, "status_code", None),
            )
            raise RuntimeError("smtp_rejected")
