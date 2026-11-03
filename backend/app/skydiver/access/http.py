"""FastAPI dependencies resolving the bearer session into an `Actor` (#146).

Usage in a beta router:

    access = AccessDependencies(service)
    @router.get("/things/{id}")
    def read(id: UUID, actor: Annotated[Actor, Depends(access.actor)]): ...

`actor` answers 401 without a valid session, `verified_actor` additionally 403
`email_unverified`, and `role(Role.REVIEWER)` 403 `forbidden`. The web server only
forwards the session; it never sends roles or owner IDs.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.skydiver.access.policy import Actor, Role, actor_roles
from app.skydiver.identity.service import IdentityService, NotAuthenticated

NO_STORE = {"cache-control": "no-store"}


def bearer_secret(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    return ""


def _denied(code: str, status_code: int) -> HTTPException:
    headers = dict(NO_STORE)
    if status_code == status.HTTP_401_UNAUTHORIZED:
        headers["www-authenticate"] = "Bearer"
    return HTTPException(status_code=status_code, detail=code, headers=headers)


class AccessDependencies:
    """Dependencies bound to one identity service (built at the composition root)."""

    def __init__(self, service: Callable[[], IdentityService]) -> None:
        def actor(secret: Annotated[str, Depends(bearer_secret)]) -> Actor:
            try:
                viewer = service().current_viewer(secret=secret)
            except NotAuthenticated:
                raise _denied(
                    "not_authenticated", status.HTTP_401_UNAUTHORIZED
                ) from None
            return Actor(
                account_id=viewer.account_id,
                person_id=viewer.person_id,
                email_verified=viewer.email_verified,
                roles=actor_roles(viewer.roles),
            )

        def verified_actor(current: Annotated[Actor, Depends(actor)]) -> Actor:
            """For private writes: the account's email must be confirmed."""
            if not current.email_verified:
                raise _denied("email_unverified", status.HTTP_403_FORBIDDEN)
            return current

        self.actor = actor
        self.verified_actor = verified_actor

    def role(self, role: Role) -> Callable[..., Actor]:
        actor = self.actor

        def require(current: Annotated[Actor, Depends(actor)]) -> Actor:
            if not current.has(role):
                raise _denied("forbidden", status.HTTP_403_FORBIDDEN)
            return current

        return require
