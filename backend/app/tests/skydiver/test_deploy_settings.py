"""#161 settings for a hosted deployment and the no-mail owner account command."""

import uuid

import pytest

from app.core.config import Settings, database_url_for_psycopg
from app.core.db import engine
from app.skydiver.identity.operator import create_confirmed, main
from app.tests.skydiver.support import Accounts

NEON = (
    "postgresql://owner:secret@ep-quiet-sea-123456.eu-central-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_a_hosted_connection_string_keeps_its_tls_settings() -> None:
    url = database_url_for_psycopg(NEON)
    assert url.startswith("postgresql+psycopg://owner:secret@ep-quiet-sea-123456.")
    assert url.endswith("/neondb?sslmode=require&channel_binding=require")
    assert (
        database_url_for_psycopg("postgres://u:p@h/db")
        == "postgresql+psycopg://u:p@h/db"
    )
    with pytest.raises(ValueError):
        database_url_for_psycopg("mysql://u:p@h/db")


def test_database_url_wins_and_one_database_is_required() -> None:
    hosted = Settings(
        PROJECT_NAME="x", DATABASE_URL=NEON, POSTGRES_SERVER="", POSTGRES_USER="",
        _env_file=None,
    )  # type: ignore[call-arg]  # fmt: skip
    assert str(hosted.SQLALCHEMY_DATABASE_URI).startswith("postgresql+psycopg://owner:")
    assert "sslmode=require" in str(hosted.SQLALCHEMY_DATABASE_URI)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings(
            PROJECT_NAME="x", DATABASE_URL=None, POSTGRES_SERVER="", POSTGRES_USER="",
            _env_file=None,
        )  # type: ignore[call-arg]  # fmt: skip


def test_the_owner_account_is_created_confirmed_without_mail() -> None:
    accounts = Accounts.create()
    email = f"Owner-{uuid.uuid4().hex[:10]}@Example.com"
    password = "a long staging passphrase"
    assert create_confirmed(engine, email=email, password=password) == "created"
    signed_in = accounts.service.login(
        email=email.lower(), password=password, client_ip="203.0.113.7"
    )
    assert signed_in.viewer.email_verified is True
    # The same address again is refused, and a weak password is refused before anything.
    assert create_confirmed(engine, email=email, password=password) == "email_in_use"
    assert create_confirmed(engine, email=f"x{email}", password="short") != "created"


def test_the_command_asks_twice_and_never_takes_a_password_argument(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(["first passphrase here", "second passphrase here"])
    code = main(["create-confirmed", "a@example.com"], ask=lambda _: next(answers))
    assert code == 1
    assert capsys.readouterr().out.strip() == "passwords_differ"
    with pytest.raises(SystemExit):
        main(["create-confirmed", "a@example.com", "--password", "x"], ask=lambda _: "")
