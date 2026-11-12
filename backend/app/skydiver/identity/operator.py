"""Operator command: create one account with a confirmed email, without sending mail.

    python -m app.skydiver.identity.operator create-confirmed you@example.com

For a deployment that has no mail sender yet (staging, owner only): registration
stays closed and the owner creates their own account here. The password is asked for
twice on the terminal and never read from arguments or the environment, so it stays
out of shell history. Run with explicit settings for the target database
(DATABASE_URL). It refuses an address that already has an account.
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlmodel import Session

from app.skydiver.adapters import AppPasswordHasher
from app.skydiver.identity import policy
from app.skydiver.identity.store import SqlIdentityStore


def create_confirmed(engine: Engine, *, email: str, password: str) -> str:
    problem = policy.password_problem(password)
    if problem:
        return problem
    email = policy.normalize_email(email)
    now = datetime.now(UTC)
    with Session(engine) as session:
        store = SqlIdentityStore(session)
        if store.email_in_use(email):
            return "email_in_use"
        account = store.create_account(
            email=email,
            password_hash=AppPasswordHasher().hash(password),
            display_name=None,
            now=now,
        )
        if not store.mark_email_verified(account.id, email, now):
            session.rollback()
            return "not_confirmed"
        session.commit()
    return "created"


def main(
    argv: Sequence[str] | None = None,
    *,
    ask: Callable[[str], str] = getpass.getpass,
) -> int:
    parser = argparse.ArgumentParser(description="Create a confirmed account.")
    parser.add_argument("command", choices=["create-confirmed"])
    parser.add_argument("email")
    args = parser.parse_args(argv)

    password = ask("Password: ")
    if password != ask("Repeat password: "):
        print("passwords_differ")
        return 1

    from app.core.db import engine  # settings are read only when run

    result = create_confirmed(engine, email=args.email, password=password)
    print(result)
    return 0 if result == "created" else 1


if __name__ == "__main__":
    sys.exit(main())
