"""HTTP adapter for identity (/api/skydiver/v1/auth). Called only by the SvelteKit server.

The browser never talks to this API: the session secret arrives as a bearer
credential from the web server, and ambient cookies are ignored.
"""

import hmac
import ipaddress
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.skydiver.identity.service import (
    ConfirmationFailed,
    IdentityError,
    IdentityService,
    InvalidCredentials,
    InvalidToken,
    MailUnavailable,
    NotAuthenticated,
    PasswordRejected,
    RegistrationClosed,
    Throttled,
    Viewer,
)

PREFIX = "/api/skydiver/v1/auth"
CLIENT_IP_HEADER = "x-organiser-client-ip"
PROXY_KEY_HEADER = "x-organiser-proxy-key"

# Bounds on input size: hashing work is only spent on bounded strings.
Password = Annotated[str, Field(min_length=1, max_length=1024)]
Token = Annotated[str, Field(min_length=1, max_length=128)]
LoginEmail = Annotated[str, Field(min_length=3, max_length=254)]


class RegisterIn(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: Password
    display_name: str | None = Field(default=None, max_length=80)


class LoginIn(BaseModel):
    email: LoginEmail
    password: Password


class TokenIn(BaseModel):
    token: Token


class ResetRequestIn(BaseModel):
    email: LoginEmail


class ResetConfirmIn(BaseModel):
    token: Token
    new_password: Password


class PasswordChangeIn(BaseModel):
    current_password: Password
    new_password: Password


class PasswordConfirmIn(BaseModel):
    password: Password


class ViewerOut(BaseModel):
    account_id: UUID
    person_id: UUID
    email: str
    display_name: str | None
    email_verified: bool
    session_expires_at: datetime


class SessionOut(BaseModel):
    session_secret: str = Field(description="Opaque; store only in an HttpOnly cookie.")
    viewer: ViewerOut


class Accepted(BaseModel):
    status: Literal["accepted"] = "accepted"


class Problem(BaseModel):
    detail: str


_STATUS: dict[type[IdentityError], int] = {
    NotAuthenticated: status.HTTP_401_UNAUTHORIZED,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    ConfirmationFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PasswordRejected: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RegistrationClosed: status.HTTP_403_FORBIDDEN,
    InvalidToken: status.HTTP_400_BAD_REQUEST,
    Throttled: status.HTTP_429_TOO_MANY_REQUESTS,
    MailUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
}

_ERRORS = {code: {"model": Problem} for code in (400, 401, 403, 422, 429, 503)}

NO_STORE = {"cache-control": "no-store"}


def _problem(error: IdentityError) -> JSONResponse:
    headers = dict(NO_STORE)
    if isinstance(error, Throttled):
        headers["retry-after"] = str(error.retry_after_seconds)
    if isinstance(error, NotAuthenticated):
        headers["www-authenticate"] = "Bearer"
    return JSONResponse(
        {"detail": error.code},
        status_code=_STATUS.get(type(error), status.HTTP_400_BAD_REQUEST),
        headers=headers,
    )


def _viewer(viewer: Viewer) -> ViewerOut:
    return ViewerOut(
        account_id=viewer.account_id,
        person_id=viewer.person_id,
        email=viewer.email,
        display_name=viewer.display_name,
        email_verified=viewer.email_verified,
        session_expires_at=viewer.session_expires_at,
    )


def _bearer(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    return ""


def client_ip_resolver(proxy_key: str | None) -> Callable[[Request], str]:
    """Trust the forwarded client IP only from the web server holding `proxy_key`."""

    def resolve(request: Request) -> str:
        if proxy_key:
            supplied = request.headers.get(PROXY_KEY_HEADER, "")
            forwarded = request.headers.get(CLIENT_IP_HEADER, "")
            if supplied and hmac.compare_digest(supplied, proxy_key):
                try:
                    return str(ipaddress.ip_address(forwarded))
                except ValueError:
                    pass
        return request.client.host if request.client else "unknown"

    return resolve


def create_router(
    *,
    service: Callable[[], IdentityService],
    client_ip: Callable[[Request], str],
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-identity"], responses=_ERRORS)  # type: ignore[arg-type]

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    Bearer = Annotated[str, Depends(_bearer)]
    deps = [Depends(no_store)]

    @router.post(
        "/registrations",
        operation_id="register",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=Accepted,
        dependencies=deps,
    )
    def register(body: RegisterIn, request: Request) -> Accepted | JSONResponse:
        try:
            service().register(
                email=str(body.email),
                password=body.password,
                display_name=body.display_name,
                client_ip=client_ip(request),
            )
        except IdentityError as error:
            return _problem(error)
        return Accepted()

    @router.post(
        "/sessions",
        operation_id="createSession",
        status_code=status.HTTP_201_CREATED,
        response_model=SessionOut,
        dependencies=deps,
    )
    def create_session(body: LoginIn, request: Request) -> SessionOut | JSONResponse:
        try:
            created = service().login(
                email=body.email, password=body.password, client_ip=client_ip(request)
            )
        except IdentityError as error:
            return _problem(error)
        return SessionOut(session_secret=created.secret, viewer=_viewer(created.viewer))

    @router.get(
        "/session",
        operation_id="getSession",
        response_model=ViewerOut,
        dependencies=deps,
    )
    def get_session(secret: Bearer) -> ViewerOut | JSONResponse:
        try:
            return _viewer(service().current_viewer(secret=secret))
        except IdentityError as error:
            return _problem(error)

    @router.delete(
        "/session",
        operation_id="deleteSession",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_session(secret: Bearer) -> Response:
        if secret:
            service().logout(secret=secret)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    @router.post(
        "/sessions/revoke-all",
        operation_id="revokeAllSessions",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def revoke_all(
        body: PasswordConfirmIn, secret: Bearer, request: Request
    ) -> Response:
        try:
            service().revoke_all(
                secret=secret, password=body.password, client_ip=client_ip(request)
            )
        except IdentityError as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    @router.post(
        "/password",
        operation_id="changePassword",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def change_password(
        body: PasswordChangeIn, secret: Bearer, request: Request
    ) -> Response:
        try:
            service().change_password(
                secret=secret,
                current_password=body.current_password,
                new_password=body.new_password,
                client_ip=client_ip(request),
            )
        except IdentityError as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    @router.post(
        "/email-verification",
        operation_id="resendVerification",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=Accepted,
        dependencies=deps,
    )
    def resend_verification(secret: Bearer) -> Accepted | JSONResponse:
        try:
            service().resend_verification(secret=secret)
        except IdentityError as error:
            return _problem(error)
        return Accepted()

    @router.post(
        "/email-verification/confirm",
        operation_id="confirmEmail",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def confirm_email(body: TokenIn) -> Response:
        try:
            service().confirm_email(token=body.token)
        except IdentityError as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    @router.post(
        "/password-reset",
        operation_id="requestPasswordReset",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=Accepted,
        dependencies=deps,
    )
    def request_reset(
        body: ResetRequestIn, request: Request
    ) -> Accepted | JSONResponse:
        try:
            service().request_password_reset(
                email=body.email, client_ip=client_ip(request)
            )
        except IdentityError as error:
            return _problem(error)
        return Accepted()

    @router.post(
        "/password-reset/confirm",
        operation_id="resetPassword",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def reset_password(body: ResetConfirmIn, request: Request) -> Response:
        try:
            service().reset_password(
                token=body.token,
                new_password=body.new_password,
                client_ip=client_ip(request),
            )
        except IdentityError as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    return router
