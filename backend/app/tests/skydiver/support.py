"""Shared helpers for beta HTTP tests: real accounts through the identity service."""

import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import update
from sqlmodel import Session, col

from app.core.db import engine
from app.models import User
from app.skydiver.adapters import AppPasswordHasher
from app.skydiver.identity.service import IdentityConfig, IdentityService
from app.skydiver.identity.store import sql_store_factory
from app.skydiver.identity.tables import SkydiverRoleGrant

PASSWORD = "correct horse battery staple"


def random_ip() -> str:
    # A fresh address per call keeps per-IP throttle windows out of tests.
    return f"10.{random.randint(150, 250)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


@dataclass
class Outbox:
    messages: list[dict[str, str]] = field(default_factory=list)

    def send(self, *, to: str, subject: str, text: str) -> None:
        self.messages.append({"to": to, "text": text})

    def token_for(self, to: str) -> str:
        for message in reversed(self.messages):
            found = re.search(r"verify-email\?token=([A-Za-z0-9_-]+)", message["text"])
            if message["to"] == to and found:
                return found.group(1)
        raise AssertionError(f"no verification mail for {to}")


@dataclass
class Accounts:
    service: IdentityService
    outbox: Outbox

    @classmethod
    def create(cls) -> Accounts:
        outbox = Outbox()
        service = IdentityService(
            stores=sql_store_factory(engine),
            hasher=AppPasswordHasher(),
            mailer=outbox,
            clock=lambda: datetime.now(UTC),
            config=IdentityConfig(
                web_origin="https://web.example",
                registration_open=True,
                max_accounts=1_000_000,
            ),
        )
        return cls(service, outbox)

    def session(
        self, *, verified: bool = True, superuser: bool = False, reviewer: bool = False
    ) -> str:
        """A real account and its session secret."""
        address = f"beta-{uuid.uuid4().hex[:12]}@example.com"
        self.service.register(
            email=address, password=PASSWORD, display_name=None, client_ip=random_ip()
        )
        if verified:
            self.service.confirm_email(token=self.outbox.token_for(address))
        with Session(engine) as session:
            user_id = session.execute(
                update(User)
                .where(col(User.email) == address)
                .values(is_superuser=superuser)
                .returning(col(User.id))
            ).scalar_one()
            if reviewer:
                session.add(
                    SkydiverRoleGrant(
                        account_id=user_id,
                        role="reviewer",
                        granted_at=datetime.now(UTC),
                    )
                )
            session.commit()
        return self.service.login(
            email=address, password=PASSWORD, client_ip=random_ip()
        ).secret
