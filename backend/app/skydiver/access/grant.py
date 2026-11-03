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
from app.skydiver.identity.tables import SkydiverRoleGrant


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
