"""Identity use cases (#145). Ports are injected; nothing here imports settings, SQL or HTTP.

Each public method is one unit of work. Mail is sent only after the transaction that
created its token has committed, so a rolled-back request never emails a live link.
"""

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.skydiver.identity import policy
from app.skydiver.identity.policy import ThrottleRule

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- ports


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify_and_update(
        self, password: str, stored_hash: str
    ) -> tuple[bool, str | None]: ...

    def burn(self, password: str) -> None:
        """Spend comparable time when no account exists (timing parity)."""
        ...


class Mailer(Protocol):
    def send(self, *, to: str, subject: str, text: str) -> None: ...


@dataclass(frozen=True)
class Account:
    id: uuid.UUID
    email: str
    password_hash: str
    is_active: bool


@dataclass(frozen=True)
class StoredSession:
    id: uuid.UUID
    account_id: uuid.UUID
    expires_at: datetime
    revoked_at: datetime | None
    credential_marker: str


@dataclass(frozen=True)
class ConsumedToken:
    account_id: uuid.UUID
    sent_to: str


@dataclass(frozen=True)
class Profile:
    person_id: uuid.UUID
    display_name: str | None
    email_verified_at: datetime | None


class IdentityStore(Protocol):
    def find_account_by_email(self, email: str) -> Account | None:
        """Unique case-insensitive match, else the exact match, else None."""
        ...

    def email_in_use(self, email: str) -> bool:
        """Any case-insensitive match, including ambiguous legacy duplicates."""
        ...

    def get_account(self, account_id: uuid.UUID) -> Account | None: ...
    def count_accounts(self) -> int: ...
    def create_account(
        self, *, email: str, password_hash: str, display_name: str | None, now: datetime
    ) -> Account: ...
    def profile(self, account_id: uuid.UUID, now: datetime) -> Profile:
        """Read the person/state rows, creating them for accounts made elsewhere."""
        ...

    def lock_account(self, account_id: uuid.UUID, now: datetime) -> Profile:
        """As `profile`, holding the account's row lock until the transaction ends."""
        ...

    def set_password_hash(
        self, account_id: uuid.UUID, password_hash: str, *, replaced: bool
    ) -> None:
        """`replaced`: a new password, recorded for replay after a restore; False
        for a rehash of the same password."""

    def roles_for(self, account_id: uuid.UUID) -> frozenset[str]:
        """Server-granted beta roles. Legacy superuser status is not one."""
        ...

    def mark_email_verified(
        self, account_id: uuid.UUID, address: str, now: datetime
    ) -> bool:
        """Verify `address` only if it is still the account's email."""
        ...

    def active_session_ids(
        self, account_id: uuid.UUID, now: datetime
    ) -> list[uuid.UUID]: ...
    def create_session(
        self,
        *,
        account_id: uuid.UUID,
        secret_hash: str,
        credential_marker: str,
        now: datetime,
        expires_at: datetime,
    ) -> uuid.UUID: ...
    def set_session_marker(self, session_id: uuid.UUID, marker: str) -> None: ...
    def carry_session_markers(
        self, *, account_id: uuid.UUID, old_marker: str, new_marker: str, now: datetime
    ) -> None:
        """Re-mark the account's live sessions issued under `old_marker`."""
        ...

    def registration_version(self) -> int:
        """Current registration gate version (read before counting accounts)."""
        ...

    def create_account_if_unchanged(
        self,
        *,
        expected_version: int,
        email: str,
        password_hash: str,
        display_name: str | None,
        now: datetime,
    ) -> Account | None:
        """Compare-and-swap: create only if the gate still has `expected_version`.

        None when another registration committed first or took the same email;
        nothing from the attempt remains.
        """
        ...

    def find_session(self, secret_hash: str) -> StoredSession | None: ...
    def delete_account(self, account_id: uuid.UUID) -> None:
        """Delete the account; its person, sessions and owned records cascade."""
        ...

    def revoke_sessions(
        self,
        *,
        now: datetime,
        reason: str,
        ids: list[uuid.UUID] | None = None,
        account_id: uuid.UUID | None = None,
        keep: uuid.UUID | None = None,
    ) -> None: ...
    def create_token(
        self,
        *,
        account_id: uuid.UUID,
        purpose: str,
        token_hash: str,
        sent_to: str,
        now: datetime,
        expires_at: datetime,
    ) -> None: ...
    def retire_tokens(
        self, *, account_id: uuid.UUID, purpose: str, now: datetime
    ) -> None: ...
    def consume_token(
        self, *, token_hash: str, purpose: str, now: datetime
    ) -> ConsumedToken | None: ...
    def throttle_count(self, *, bucket: str, key_hash: str, since: datetime) -> int: ...
    def throttle_record(self, *, bucket: str, key_hash: str, now: datetime) -> None: ...


StoreFactory = Callable[[], AbstractContextManager[IdentityStore]]
Clock = Callable[[], datetime]

# -------------------------------------------------------------------------- results


# Compare-and-swap rounds per registration. Each lost round means another account
# was committed meanwhile, so exhaustion needs sustained concurrent sign-ups.
REGISTRATION_ATTEMPTS = 8


class IdentityError(Exception):
    code = "identity_error"


class NotAuthenticated(IdentityError):
    code = "not_authenticated"


class InvalidCredentials(IdentityError):
    code = "invalid_credentials"


class ConfirmationFailed(IdentityError):
    code = "password_confirmation_failed"


class RegistrationClosed(IdentityError):
    code = "registration_closed"


class RegistrationBusy(IdentityError):
    """Concurrent registrations kept winning the compare-and-swap; retry later."""

    code = "registration_busy"


class InvalidToken(IdentityError):
    code = "invalid_or_expired_token"


class MailUnavailable(IdentityError):
    code = "mail_unavailable"


class PasswordRejected(IdentityError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Throttled(IdentityError):
    code = "too_many_attempts"

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(self.code)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class Viewer:
    account_id: uuid.UUID
    person_id: uuid.UUID
    email: str
    display_name: str | None
    email_verified: bool
    session_expires_at: datetime
    # Authorization input for the access layer (#146). The API echoes the viewer's own
    # roles so the web app can link reviewer tools; the API still enforces them.
    roles: frozenset[str] = frozenset()


@dataclass(frozen=True)
class NewSession:
    secret: str
    viewer: Viewer


@dataclass(frozen=True)
class IdentityConfig:
    web_origin: str
    registration_open: bool
    max_accounts: int
    product_name: str = "Load Organiser"


# ------------------------------------------------------------------------ use cases


@dataclass
class _Outbox:
    """Mail queued during a transaction and sent only after it commits."""

    messages: list[tuple[str, str, str]]

    def add(self, to: str, subject: str, text: str) -> None:
        self.messages.append((to, subject, text))


class IdentityService:
    def __init__(
        self,
        *,
        stores: StoreFactory,
        hasher: PasswordHasher,
        mailer: Mailer | None,
        clock: Clock,
        config: IdentityConfig,
    ) -> None:
        self._stores = stores
        self._hasher = hasher
        self._mailer = mailer
        self._clock = clock
        self._config = config

    # -- registration and verification ------------------------------------------

    def register(
        self, *, email: str, password: str, display_name: str | None, client_ip: str
    ) -> None:
        """Neutral: the caller learns nothing about whether the email already exists."""
        client_ip = policy.client_bucket(client_ip)
        problem = policy.password_problem(password)
        if problem:
            raise PasswordRejected(problem)
        self._require_mailer()
        email = policy.normalize_email(email)
        name = (display_name or "").strip() or None
        now = self._clock()
        outbox = _Outbox([])

        with self._stores() as store:
            self._check(store, policy.REGISTER_IP, now, client_ip)
            self._hit(store, policy.REGISTER_IP, now, client_ip)
            if not self._config.registration_open:
                raise CommitThen(RegistrationClosed())
            # Hash before branching so both outcomes cost the same Argon2 work, but
            # only once the per-IP limit has admitted the request.
            password_hash = self._hasher.hash(password)
            # Compare-and-swap instead of a lock: read the gate version, then count
            # and check the email; the insert commits only if the gate is unchanged.
            # Otherwise another registration committed first, so re-read and retry.
            # The cap applies before the email lookup so a full service answers the
            # same way for taken and unused addresses.
            version = store.registration_version()
            if store.count_accounts() >= self._config.max_accounts:
                raise CommitThen(RegistrationClosed())
            if self._exceeded(store, policy.REGISTER_IDENTIFIER, now, email):
                # Silent, like the reset identifier limit: bounds mail to one inbox.
                return
            self._hit(store, policy.REGISTER_IDENTIFIER, now, email)
            for _ in range(REGISTRATION_ATTEMPTS):
                if store.email_in_use(email):
                    outbox.add(
                        email,
                        f"{self._config.product_name}: sign-in help",
                        "Someone tried to create an account with this email address, "
                        "which already has one.\n\nIf it was you, sign in or reset "
                        f"your password at {self._config.web_origin}/forgot-password"
                        "\n\nIf it was not you, you can ignore this message.",
                    )
                    break
                account = store.create_account_if_unchanged(
                    expected_version=version,
                    email=email,
                    password_hash=password_hash,
                    display_name=name,
                    now=now,
                )
                if account is not None:
                    outbox.add(*self._verification_mail(store, account, now))
                    break
                version = store.registration_version()
                if store.count_accounts() >= self._config.max_accounts:
                    raise CommitThen(RegistrationClosed())
            else:
                # Sustained contention: keep the throttle hits, report a retryable state.
                raise CommitThen(RegistrationBusy())
        self._flush(outbox)

    def resend_verification(self, *, secret: str) -> None:
        now = self._clock()
        outbox = _Outbox([])
        with self._stores() as store:
            # Who is asking comes first: a caller without a session learns nothing,
            # not even whether mail is working.
            account, profile, _ = self._authenticated(store, secret, now)
            self._require_mailer()
            if profile.email_verified_at is not None:
                return
            key = str(account.id)
            self._check(store, policy.VERIFY_RESEND_ACCOUNT, now, key)
            self._hit(store, policy.VERIFY_RESEND_ACCOUNT, now, key)
            outbox.add(*self._verification_mail(store, account, now))
        self._flush(outbox)

    def confirm_email(self, *, token: str) -> None:
        now = self._clock()
        with self._stores() as store:
            consumed = store.consume_token(
                token_hash=policy.hash_secret(token), purpose="verify_email", now=now
            )
            if consumed is None:
                raise InvalidToken()
            store.lock_account(consumed.account_id, now)
            # A link sent to a previous address does not verify the current one.
            if not store.mark_email_verified(
                consumed.account_id, consumed.sent_to, now
            ):
                raise InvalidToken()

    # -- sessions -----------------------------------------------------------------

    def login(self, *, email: str, password: str, client_ip: str) -> NewSession:
        client_ip = policy.client_bucket(client_ip)
        email = policy.normalize_email(email)
        now = self._clock()
        failed = False
        result: NewSession | None = None
        with self._stores() as store:
            self._check(store, policy.LOGIN_IP, now, client_ip)
            self._check(store, policy.LOGIN_PAIR, now, client_ip, email)
            account = store.find_account_by_email(email)
            if account is None:
                self._hasher.burn(password)
                verified, updated = False, None
            else:
                verified, updated = self._hasher.verify_and_update(
                    password, account.password_hash
                )
            if account is None or not verified or not account.is_active:
                self._hit(store, policy.LOGIN_IP, now, client_ip)
                self._hit(store, policy.LOGIN_PAIR, now, client_ip, email)
                failed = True
            else:
                profile = store.lock_account(account.id, now)
                current_hash = account.password_hash
                if updated:
                    # #170 compatibility: legacy bcrypt is upgraded to Argon2id. Same
                    # password, new encoding: live sessions must survive the rehash.
                    store.set_password_hash(account.id, updated, replaced=False)
                    store.carry_session_markers(
                        account_id=account.id,
                        old_marker=policy.credential_marker(account.password_hash),
                        new_marker=policy.credential_marker(updated),
                        now=now,
                    )
                    current_hash = updated
                result = self._open_session(store, account, profile, now, current_hash)
        if failed or result is None:
            raise InvalidCredentials()
        return result

    def current_viewer(self, *, secret: str) -> Viewer:
        now = self._clock()
        with self._stores() as store:
            account, profile, session = self._authenticated(store, secret, now)
            return self._viewer(
                account, profile, session.expires_at, store.roles_for(account.id)
            )

    def logout(self, *, secret: str) -> None:
        """Idempotent: an unknown or already revoked secret is not an error."""
        now = self._clock()
        with self._stores() as store:
            session = store.find_session(policy.hash_secret(secret))
            if session is not None and session.revoked_at is None:
                store.revoke_sessions(now=now, reason="logout", ids=[session.id])

    def confirm_password(self, *, secret: str, password: str, client_ip: str) -> None:
        """Fresh password confirmation for a sensitive operation (e.g. restore).

        Shares the login failure budget; raises ConfirmationFailed or Throttled.
        """
        client_ip = policy.client_bucket(client_ip)
        now = self._clock()
        with self._stores() as store:
            account, _, _ = self._authenticated(store, secret, now)
            self._confirm_password(store, account, password, now, client_ip)

    def consume(self, *, rule: ThrottleRule, key: str) -> None:
        """Count one attempt against `rule` for `key`; Throttled when over the limit."""
        now = self._clock()
        with self._stores() as store:
            self._check(store, rule, now, key)
            self._hit(store, rule, now, key)

    def revoke_all(self, *, secret: str, password: str, client_ip: str) -> None:
        client_ip = policy.client_bucket(client_ip)
        now = self._clock()
        with self._stores() as store:
            account, _, _ = self._authenticated(store, secret, now)
            self._confirm_password(store, account, password, now, client_ip)
            store.revoke_sessions(now=now, reason="revoke_all", account_id=account.id)

    def delete_account(self, *, secret: str, password: str, client_ip: str) -> None:
        """Delete the caller's account and everything it owns, after a fresh password.

        One transaction: the session, profile, follows, blocks, posts, logbook, gear,
        places, history, saves, plans, restore receipts and reports by or about the
        person go together. Directory and moderation history keep their records with
        the person reference cleared (foreign keys SET NULL).
        """
        client_ip = policy.client_bucket(client_ip)
        now = self._clock()
        with self._stores() as store:
            account, _, _ = self._authenticated(store, secret, now)
            self._confirm_password(store, account, password, now, client_ip)
            store.delete_account(account.id)

    def change_password(
        self, *, secret: str, current_password: str, new_password: str, client_ip: str
    ) -> None:
        client_ip = policy.client_bucket(client_ip)
        problem = policy.password_problem(new_password)
        if problem:
            raise PasswordRejected(problem)
        now = self._clock()
        with self._stores() as store:
            account, _, session = self._authenticated(store, secret, now)
            self._confirm_password(store, account, current_password, now, client_ip)
            # Hashed only after the session and current password are proven.
            new_hash = self._hasher.hash(new_password)
            store.lock_account(account.id, now)
            store.set_password_hash(account.id, new_hash, replaced=True)
            # The current session survives the change; every other one is revoked.
            store.set_session_marker(session.id, policy.credential_marker(new_hash))
            store.retire_tokens(
                account_id=account.id, purpose="reset_password", now=now
            )
            store.revoke_sessions(
                now=now,
                reason="password_changed",
                account_id=account.id,
                keep=session.id,
            )

    # -- recovery -----------------------------------------------------------------

    def request_password_reset(self, *, email: str, client_ip: str) -> None:
        """Always neutral for the identifier; only the per-IP limit is visible."""
        client_ip = policy.client_bucket(client_ip)
        self._require_mailer()
        email = policy.normalize_email(email)
        now = self._clock()
        outbox = _Outbox([])
        with self._stores() as store:
            self._check(store, policy.RESET_IP, now, client_ip)
            self._hit(store, policy.RESET_IP, now, client_ip)
            if self._exceeded(store, policy.RESET_IDENTIFIER, now, email):
                return
            self._hit(store, policy.RESET_IDENTIFIER, now, email)
            account = store.find_account_by_email(email)
            if account is None or not account.is_active:
                return
            store.lock_account(account.id, now)
            store.retire_tokens(
                account_id=account.id, purpose="reset_password", now=now
            )
            token = policy.new_secret()
            store.create_token(
                account_id=account.id,
                purpose="reset_password",
                token_hash=policy.hash_secret(token),
                sent_to=account.email,
                now=now,
                expires_at=now + policy.ACCOUNT_TOKEN_LIFETIME,
            )
            outbox.add(
                account.email,
                f"{self._config.product_name}: reset your password",
                "Use this link within 30 minutes to choose a new password. It works "
                f"once.\n\n{self._config.web_origin}/reset-password?token={token}\n\n"
                "Resetting signs you out on every device. If you did not ask for "
                "this, ignore this message; your password has not changed.",
            )
        self._flush(outbox, neutral=True)

    def reset_password(self, *, token: str, new_password: str, client_ip: str) -> None:
        client_ip = policy.client_bucket(client_ip)
        problem = policy.password_problem(new_password)
        if problem:
            raise PasswordRejected(problem)
        now = self._clock()
        with self._stores() as store:
            consumed = store.consume_token(
                token_hash=policy.hash_secret(token), purpose="reset_password", now=now
            )
            account = store.get_account(consumed.account_id) if consumed else None
            if (
                consumed is None
                or account is None
                or not account.is_active
                # Issued to an address the account no longer uses.
                or consumed.sent_to.lower() != account.email.lower()
            ):
                # Only the failure path is limited: a live link is never refused
                # because others behind the same address guessed badly.
                if self._exceeded(store, policy.RESET_CONFIRM_IP, now, client_ip):
                    raise CommitThen(
                        Throttled(int(policy.RESET_CONFIRM_IP.window.total_seconds()))
                    )
                self._hit(store, policy.RESET_CONFIRM_IP, now, client_ip)
                raise CommitThen(InvalidToken())
            # Hashed only once a live token has been consumed.
            new_hash = self._hasher.hash(new_password)
            store.lock_account(account.id, now)
            store.set_password_hash(account.id, new_hash, replaced=True)
            # The reset link proved control of the inbox it was sent to.
            store.mark_email_verified(account.id, consumed.sent_to, now)
            store.retire_tokens(
                account_id=account.id, purpose="reset_password", now=now
            )
            store.revoke_sessions(
                now=now, reason="password_reset", account_id=account.id
            )

    # -- helpers ------------------------------------------------------------------

    def _authenticated(
        self, store: IdentityStore, secret: str, now: datetime
    ) -> tuple[Account, Profile, StoredSession]:
        if not secret:
            raise NotAuthenticated()
        session = store.find_session(policy.hash_secret(secret))
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            raise NotAuthenticated()
        account = store.get_account(session.account_id)
        if (
            account is None
            or not account.is_active
            or session.credential_marker
            != policy.credential_marker(account.password_hash)
        ):
            # Suspension takes effect on the next request, without a session sweep.
            raise NotAuthenticated()
        profile = store.profile(account.id, now)
        return account, profile, session

    def _open_session(
        self,
        store: IdentityStore,
        account: Account,
        profile: Profile,
        now: datetime,
        password_hash: str,
    ) -> NewSession:
        over = policy.sessions_over_cap(store.active_session_ids(account.id, now))
        if over:
            store.revoke_sessions(now=now, reason="session_limit", ids=over)
        secret = policy.new_secret()
        expires_at = policy.session_expiry(now)
        store.create_session(
            account_id=account.id,
            secret_hash=policy.hash_secret(secret),
            credential_marker=policy.credential_marker(password_hash),
            now=now,
            expires_at=expires_at,
        )
        return NewSession(
            secret=secret, viewer=self._viewer(account, profile, expires_at)
        )

    def _confirm_password(
        self,
        store: IdentityStore,
        account: Account,
        password: str,
        now: datetime,
        client_ip: str,
    ) -> None:
        # Same key as login (normalised), so both share one failure budget.
        identifier = policy.normalize_email(account.email)
        self._check(store, policy.LOGIN_PAIR, now, client_ip, identifier)
        ok, _ = self._hasher.verify_and_update(password, account.password_hash)
        if not ok:
            self._hit(store, policy.LOGIN_PAIR, now, client_ip, identifier)
            raise CommitThen(ConfirmationFailed())

    def _verification_mail(
        self, store: IdentityStore, account: Account, now: datetime
    ) -> tuple[str, str, str]:
        store.retire_tokens(account_id=account.id, purpose="verify_email", now=now)
        token = policy.new_secret()
        store.create_token(
            account_id=account.id,
            purpose="verify_email",
            token_hash=policy.hash_secret(token),
            sent_to=account.email,
            now=now,
            expires_at=now + policy.ACCOUNT_TOKEN_LIFETIME,
        )
        return (
            account.email,
            f"{self._config.product_name}: confirm your email",
            "Confirm this email address within 30 minutes to start saving private "
            f"records:\n\n{self._config.web_origin}/verify-email?token={token}\n\n"
            "If you did not create an account, ignore this message.",
        )

    def _viewer(
        self,
        account: Account,
        profile: Profile,
        expires_at: datetime,
        roles: frozenset[str] = frozenset(),
    ) -> Viewer:
        return Viewer(
            account_id=account.id,
            person_id=profile.person_id,
            email=account.email,
            display_name=profile.display_name,
            email_verified=profile.email_verified_at is not None,
            session_expires_at=expires_at,
            roles=roles,
        )

    def _exceeded(
        self, store: IdentityStore, rule: ThrottleRule, now: datetime, *parts: str
    ) -> bool:
        count = store.throttle_count(
            bucket=rule.bucket,
            key_hash=policy.throttle_key(rule.bucket, *parts),
            since=now - rule.window,
        )
        return count >= rule.limit

    def _check(
        self, store: IdentityStore, rule: ThrottleRule, now: datetime, *parts: str
    ) -> None:
        if self._exceeded(store, rule, now, *parts):
            raise Throttled(int(rule.window.total_seconds()))

    def _hit(
        self, store: IdentityStore, rule: ThrottleRule, now: datetime, *parts: str
    ) -> None:
        store.throttle_record(
            bucket=rule.bucket,
            key_hash=policy.throttle_key(rule.bucket, *parts),
            now=now,
        )

    def _require_mailer(self) -> None:
        if self._mailer is None:
            raise MailUnavailable()

    def _flush(self, outbox: _Outbox, *, neutral: bool = False) -> None:
        """Send queued mail after commit.

        With `neutral`, delivery failures are logged, not raised: a 503 only when an
        account exists would reveal that it exists.
        """
        if self._mailer is None:
            raise MailUnavailable()
        for to, subject, text in outbox.messages:
            try:
                self._mailer.send(to=to, subject=subject, text=text)
            except Exception as exc:
                logger.warning("Identity mail failed: %s", type(exc).__name__)
                if not neutral:
                    raise MailUnavailable() from None


class CommitThen(Exception):
    """Raised inside a unit of work whose writes (e.g. throttle hits) must commit
    before `error` reaches the caller. Store factories commit, then raise `error`.
    """

    def __init__(self, error: IdentityError) -> None:
        super().__init__(error.code)
        self.error = error
