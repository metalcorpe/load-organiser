"""Operator command: grant or revoke a server-granted beta role (#146, #148).

    python -m app.skydiver.access.grant reviewer someone@example.com
    python -m app.skydiver.access.grant reviewer someone@example.com --revoke

Run with explicit settings for the target database. There is no HTTP API for roles.
A grant takes effect on the account's next request; revocation likewise.
"""

import argparse
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col

from app.models import User
from app.skydiver.access.policy import Role
from app.skydiver.identity.tables import SkydiverAccountState, SkydiverRoleGrant


def set_role(engine: Engine, *, email: str, role: Role, grant: bool) -> str:
    with Session(engine) as session:
        users = (
            session.execute(
                select(User).where(func.lower(col(User.email)) == email.strip().lower())
            )
            .scalars()
            .all()
        )
        if len(users) != 1:
            return "no_unique_account"
        account_id = users[0].id
        if grant:
            session.execute(
                insert(SkydiverRoleGrant)
                .values(
                    id=uuid.uuid4(),
                    account_id=account_id,
                    role=role.value,
                    granted_at=datetime.now(UTC),
                )
                .on_conflict_do_nothing(constraint="uq_skydiver_role_grant")
            )
        else:
            session.execute(
                delete(SkydiverRoleGrant)
                .where(col(SkydiverRoleGrant.account_id) == account_id)
                .where(col(SkydiverRoleGrant.role) == role.value)
            )
        session.commit()
    return "granted" if grant else "revoked"


def bootstrap_reviewer(engine: Engine, *, email: str) -> str:
    """The configured owner's reviewer role, only once that address is confirmed.

    Registration may be open while this runs at start-up, so anyone could create an
    account with the owner's address first; holding the address is not enough. The
    account's current email must be the configured one and that same address must
    have been confirmed (`email_verified_for`), or nothing is granted.
    """
    address = email.strip().lower()
    with Session(engine) as session:
        rows = session.execute(
            select(
                col(User.id),
                col(SkydiverAccountState.email_verified_at),
                col(SkydiverAccountState.email_verified_for),
            )
            .join(
                SkydiverAccountState,
                col(SkydiverAccountState.account_id) == col(User.id),
            )
            .where(func.lower(col(User.email)) == address)
        ).all()
    if len(rows) != 1:
        return "no_unique_account"
    _, verified_at, verified_for = rows[0]
    if verified_at is None or (verified_for or "").lower() != address:
        return "not_confirmed"
    return set_role(engine, email=address, role=Role.REVIEWER, grant=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grant or revoke a beta role.")
    parser.add_argument("role", choices=[r.value for r in Role])
    parser.add_argument("email")
    parser.add_argument("--revoke", action="store_true")
    args = parser.parse_args(argv)

    from app.core.db import engine  # settings are read only when run

    result = set_role(
        engine, email=args.email, role=Role(args.role), grant=not args.revoke
    )
    print(result)
    return 0 if result in ("granted", "revoked") else 1


if __name__ == "__main__":
    sys.exit(main())
