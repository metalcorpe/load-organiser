"""SQL adapter for `IdentityStore`. Composition-root only; policy never imports it."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col

from app.models import User
from app.skydiver.identity.service import (
    Account,
    CommitThen,
    ConsumedToken,
    IdentityStore,
    Profile,
    StoredSession,
    StoreFactory,
)
from app.skydiver.identity.tables import (
    SkydiverAccountState,
    SkydiverAccountToken,
    SkydiverPerson,
    SkydiverRoleGrant,
    SkydiverSession,
    SkydiverThrottleEvent,
)

# Arbitrary fixed key for pg_advisory_xact_lock; unique within this database's code.
_REGISTRATION_LOCK_KEY = 0x5B1E_7C2A_0145


def _account(user: User) -> Account:
    return Account(
        id=user.id,
        email=user.email,
        password_hash=user.hashed_password,
        is_active=user.is_active,
    )


class SqlIdentityStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    # accounts -----------------------------------------------------------------

    def _matches(self, email: str) -> list[User]:
        # Legacy rows may hold mixed-case emails; compare case-insensitively.
        return list(
            self._s.execute(select(User).where(func.lower(col(User.email)) == email))
            .scalars()
            .all()
        )

    def find_account_by_email(self, email: str) -> Account | None:
        users = self._matches(email)
        if len(users) == 1:
            return _account(users[0])
        # Case-only legacy duplicates: only an exact match, otherwise none.
        exact = [user for user in users if user.email == email]
        return _account(exact[0]) if len(exact) == 1 else None

    def email_in_use(self, email: str) -> bool:
        return bool(self._matches(email))

    def get_account(self, account_id: uuid.UUID) -> Account | None:
        user = self._s.get(User, account_id)
        return _account(user) if user else None

    def count_accounts(self) -> int:
        return int(self._s.execute(select(func.count()).select_from(User)).scalar_one())

    def create_account(
        self, *, email: str, password_hash: str, display_name: str | None, now: datetime
    ) -> Account:
        user = User(email=email, hashed_password=password_hash, full_name=display_name)
        self._s.add(user)
        self._s.flush()
        self._ensure_identity(user.id, now, display_name)
        return _account(user)

    def _ensure_identity(
        self, account_id: uuid.UUID, now: datetime, display_name: str | None = None
    ) -> None:
        self._s.execute(
            insert(SkydiverPerson)
            .values(
                id=uuid.uuid4(),
                account_id=account_id,
                display_name=display_name,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=["account_id"])
        )
        self._s.execute(
            insert(SkydiverAccountState)
            .values(account_id=account_id, created_at=now)
            .on_conflict_do_nothing(index_elements=["account_id"])
        )

    def _profile(self, account_id: uuid.UUID, now: datetime, *, lock: bool) -> Profile:
        state_query = select(SkydiverAccountState).where(
            col(SkydiverAccountState.account_id) == account_id
        )
        if lock:
            state_query = state_query.with_for_update()
        state = self._s.execute(state_query).scalars().first()
        if state is None:
            self._ensure_identity(account_id, now)
            state = self._s.execute(state_query).scalars().one()
        person = (
            self._s.execute(
                select(SkydiverPerson).where(
                    col(SkydiverPerson.account_id) == account_id
                )
            )
            .scalars()
            .one()
        )
        email = self._s.execute(
            select(col(User.email)).where(col(User.id) == account_id)
        ).scalar_one()
        # Verification covers the address that was verified, not later changes.
        verified = (
            state.email_verified_at
            if state.email_verified_for is not None
            and state.email_verified_for.lower() == email.lower()
            else None
        )
        return Profile(
            person_id=person.id,
            display_name=person.display_name,
            email_verified_at=verified,
        )

    def profile(self, account_id: uuid.UUID, now: datetime) -> Profile:
        return self._profile(account_id, now, lock=False)

    def lock_account(self, account_id: uuid.UUID, now: datetime) -> Profile:
        return self._profile(account_id, now, lock=True)

    def set_password_hash(self, account_id: uuid.UUID, password_hash: str) -> None:
        self._s.execute(
            update(User)
            .where(col(User.id) == account_id)
            .values(hashed_password=password_hash)
        )

    def roles_for(self, account_id: uuid.UUID) -> frozenset[str]:
        rows = self._s.execute(
            select(col(SkydiverRoleGrant.role)).where(
                col(SkydiverRoleGrant.account_id) == account_id
            )
        ).all()
        return frozenset(row[0] for row in rows)

    def mark_email_verified(
        self, account_id: uuid.UUID, address: str, now: datetime
    ) -> bool:
        current = self._s.execute(
            select(col(User.email)).where(col(User.id) == account_id)
        ).scalar_one()
        if current.lower() != address.lower():
            return False
        self._s.execute(
            update(SkydiverAccountState)
            .where(col(SkydiverAccountState.account_id) == account_id)
            .values(email_verified_at=now, email_verified_for=current)
        )
        return True

    # sessions -------------------------------------------------------------------

    def active_session_ids(
        self, account_id: uuid.UUID, now: datetime
    ) -> list[uuid.UUID]:
        rows = self._s.execute(
            select(col(SkydiverSession.id))
            .where(col(SkydiverSession.account_id) == account_id)
            .where(col(SkydiverSession.revoked_at).is_(None))
            .where(col(SkydiverSession.expires_at) > now)
            .order_by(col(SkydiverSession.created_at), col(SkydiverSession.id))
        ).all()
        return [row[0] for row in rows]

    def create_session(
        self,
        *,
        account_id: uuid.UUID,
        secret_hash: str,
        credential_marker: str,
        now: datetime,
        expires_at: datetime,
    ) -> uuid.UUID:
        row = SkydiverSession(
            account_id=account_id,
            secret_hash=secret_hash,
            credential_marker=credential_marker,
            created_at=now,
            expires_at=expires_at,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def set_session_marker(self, session_id: uuid.UUID, marker: str) -> None:
        self._s.execute(
            update(SkydiverSession)
            .where(col(SkydiverSession.id) == session_id)
            .values(credential_marker=marker)
        )

    def carry_session_markers(
        self, *, account_id: uuid.UUID, old_marker: str, new_marker: str, now: datetime
    ) -> None:
        self._s.execute(
            update(SkydiverSession)
            .where(col(SkydiverSession.account_id) == account_id)
            .where(col(SkydiverSession.credential_marker) == old_marker)
            .where(col(SkydiverSession.revoked_at).is_(None))
            .where(col(SkydiverSession.expires_at) > now)
            .values(credential_marker=new_marker)
        )

    def lock_registrations(self) -> None:
        # Transaction-scoped; released on commit or rollback.
        self._s.execute(select(func.pg_advisory_xact_lock(_REGISTRATION_LOCK_KEY)))

    def find_session(self, secret_hash: str) -> StoredSession | None:
        s = (
            self._s.execute(
                select(SkydiverSession).where(
                    col(SkydiverSession.secret_hash) == secret_hash
                )
            )
            .scalars()
            .first()
        )
        if s is None:
            return None
        return StoredSession(
            id=s.id,
            account_id=s.account_id,
            expires_at=s.expires_at,
            revoked_at=s.revoked_at,
            credential_marker=s.credential_marker,
        )

    def revoke_sessions(
        self,
        *,
        now: datetime,
        reason: str,
        ids: list[uuid.UUID] | None = None,
        account_id: uuid.UUID | None = None,
        keep: uuid.UUID | None = None,
    ) -> None:
        if ids is None and account_id is None:
            raise ValueError("revoke_sessions needs ids or account_id")
        statement = (
            update(SkydiverSession)
            .where(col(SkydiverSession.revoked_at).is_(None))
            .values(revoked_at=now, revoke_reason=reason)
        )
        if ids is not None:
            statement = statement.where(col(SkydiverSession.id).in_(ids))
        if account_id is not None:
            statement = statement.where(col(SkydiverSession.account_id) == account_id)
        if keep is not None:
            statement = statement.where(col(SkydiverSession.id) != keep)
        self._s.execute(statement)

    # tokens ---------------------------------------------------------------------

    def create_token(
        self,
        *,
        account_id: uuid.UUID,
        purpose: str,
        token_hash: str,
        sent_to: str,
        now: datetime,
        expires_at: datetime,
    ) -> None:
        self._s.add(
            SkydiverAccountToken(
                account_id=account_id,
                purpose=purpose,
                token_hash=token_hash,
                sent_to=sent_to,
                created_at=now,
                expires_at=expires_at,
            )
        )
        self._s.flush()

    def retire_tokens(
        self, *, account_id: uuid.UUID, purpose: str, now: datetime
    ) -> None:
        self._s.execute(
            update(SkydiverAccountToken)
            .where(col(SkydiverAccountToken.account_id) == account_id)
            .where(col(SkydiverAccountToken.purpose) == purpose)
            .where(col(SkydiverAccountToken.used_at).is_(None))
            .values(used_at=now)
        )

    def consume_token(
        self, *, token_hash: str, purpose: str, now: datetime
    ) -> ConsumedToken | None:
        # Single statement: concurrent consumers cannot both succeed.
        row = self._s.execute(
            update(SkydiverAccountToken)
            .where(col(SkydiverAccountToken.token_hash) == token_hash)
            .where(col(SkydiverAccountToken.purpose) == purpose)
            .where(col(SkydiverAccountToken.used_at).is_(None))
            .where(col(SkydiverAccountToken.expires_at) > now)
            .values(used_at=now)
            .returning(
                col(SkydiverAccountToken.account_id), col(SkydiverAccountToken.sent_to)
            )
        ).first()
        return ConsumedToken(account_id=row[0], sent_to=row[1]) if row else None

    # throttling -----------------------------------------------------------------

    def throttle_count(self, *, bucket: str, key_hash: str, since: datetime) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(SkydiverThrottleEvent)
                .where(col(SkydiverThrottleEvent.bucket) == bucket)
                .where(col(SkydiverThrottleEvent.key_hash) == key_hash)
                .where(col(SkydiverThrottleEvent.created_at) > since)
            ).scalar_one()
        )

    def throttle_record(self, *, bucket: str, key_hash: str, now: datetime) -> None:
        self._s.add(
            SkydiverThrottleEvent(bucket=bucket, key_hash=key_hash, created_at=now)
        )
        self._s.flush()


def sql_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success or `CommitThen`, roll back on anything else."""

    @contextmanager
    def stores() -> Iterator[IdentityStore]:
        with Session(engine) as session:
            try:
                yield SqlIdentityStore(session)
            except CommitThen as pending:
                session.commit()
                raise pending.error from None
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
