from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine
from app.skydiver.adapters import (
    AppPasswordHasher,
    cached_probe,
    create_probe_engine,
    sql_database_probe,
)
from app.skydiver.api import create_router as create_skydiver_router
from app.skydiver.health import utc_now
from app.skydiver.identity.api import client_ip_resolver
from app.skydiver.identity.api import create_router as create_identity_router
from app.skydiver.identity.mail import FileOutboxMailer, SmtpMailer
from app.skydiver.identity.service import IdentityConfig, IdentityService, Mailer
from app.skydiver.identity.store import sql_store_factory


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Skydiver beta namespace (/api/skydiver/v1); legacy isolation is #146.
health_probe = cached_probe(
    sql_database_probe(create_probe_engine(str(settings.SQLALCHEMY_DATABASE_URI)))
)
app.include_router(create_skydiver_router(database_probe=health_probe))


def _identity_mailer() -> Mailer | None:
    if settings.SKYDIVER_MAIL_OUTBOX_DIR:
        return FileOutboxMailer(Path(settings.SKYDIVER_MAIL_OUTBOX_DIR))
    if settings.SMTP_HOST and settings.EMAILS_FROM_EMAIL:
        return SmtpMailer(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_TLS,
            use_ssl=settings.SMTP_SSL,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_email=str(settings.EMAILS_FROM_EMAIL),
            from_name=settings.EMAILS_FROM_NAME,
        )
    return None


identity_service = IdentityService(
    stores=sql_store_factory(engine),
    hasher=AppPasswordHasher(),
    mailer=_identity_mailer(),
    clock=utc_now,
    config=IdentityConfig(
        web_origin=settings.SKYDIVER_WEB_ORIGIN.rstrip("/"),
        registration_open=settings.SKYDIVER_REGISTRATION_OPEN,
        max_accounts=settings.SKYDIVER_MAX_ACCOUNTS,
        product_name=settings.PROJECT_NAME,
    ),
)
app.include_router(
    create_identity_router(
        service=lambda: identity_service,
        client_ip=client_ip_resolver(settings.SKYDIVER_WEB_PROXY_KEY),
    )
)
