from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.adapters import (
    AppPasswordHasher,
    cached_probe,
    create_probe_engine,
    sql_database_probe,
)
from app.skydiver.api import create_router as create_skydiver_router
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.health import utc_now
from app.skydiver.identity.api import client_ip_resolver
from app.skydiver.identity.api import create_router as create_identity_router
from app.skydiver.identity.mail import FileOutboxMailer, SmtpMailer
from app.skydiver.identity.service import IdentityConfig, IdentityService, Mailer
from app.skydiver.identity.store import sql_store_factory
from app.skydiver.moderation.api import create_router as create_moderation_router
from app.skydiver.moderation.service import SubmissionService
from app.skydiver.moderation.store import sql_submission_store_factory
from app.skydiver.opportunities.api import create_router as create_opportunity_router
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.skydiver.saves.api import create_router as create_saves_router
from app.skydiver.saves.service import SavesService
from app.skydiver.saves.store import sql_saves_store_factory


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

health_probe = cached_probe(
    sql_database_probe(create_probe_engine(str(settings.SQLALCHEMY_DATABASE_URI)))
)


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
directory_service = DirectoryService(
    stores=sql_directory_store_factory(engine), clock=utc_now
)
opportunity_service = OpportunityService(
    stores=sql_listing_store_factory(engine),
    clock=utc_now,
)
saves_service = SavesService(
    stores=sql_saves_store_factory(engine),
    clock=utc_now,
    opportunities=opportunity_service,
    directory=directory_service,
)

submission_service = SubmissionService(
    stores=sql_submission_store_factory(engine),
    clock=utc_now,
    directory=directory_service,
    opportunities=opportunity_service,
    is_open=lambda: settings.SKYDIVER_SUBMISSIONS_OPEN,
)


def create_app(*, include_legacy: bool) -> FastAPI:
    """Compose the API. The beta namespace is always mounted; legacy only on request.

    `include_legacy` must come from `settings.LEGACY_API_ENABLED`, which settings
    refuse outside ENVIRONMENT=local, or from tests of the legacy prototype (#146).
    """
    local = settings.ENVIRONMENT == "local"
    application = FastAPI(
        title=settings.PROJECT_NAME,
        generate_unique_id_function=custom_generate_unique_id,
        # Outside local nothing but the beta allowlist is served, not even docs.
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if local else None,
        docs_url="/docs" if local else None,
        redoc_url="/redoc" if local else None,
    )
    application.include_router(create_skydiver_router(database_probe=health_probe))
    application.include_router(
        create_identity_router(
            service=lambda: identity_service,
            client_ip=client_ip_resolver(settings.SKYDIVER_WEB_PROXY_KEY),
        )
    )
    application.include_router(
        create_directory_router(
            service=lambda: directory_service,
            access=AccessDependencies(lambda: identity_service),
        )
    )
    application.include_router(
        create_opportunity_router(
            service=lambda: opportunity_service,
            access=AccessDependencies(lambda: identity_service),
        )
    )
    application.include_router(
        create_moderation_router(
            service=lambda: submission_service,
            access=AccessDependencies(lambda: identity_service),
        )
    )
    application.include_router(
        create_saves_router(
            service=lambda: saves_service,
            access=AccessDependencies(lambda: identity_service),
        )
    )
    if include_legacy:
        # The beta API is called server-to-server by the web app and needs no CORS;
        # only the legacy React client calls the API from a browser.
        if settings.all_cors_origins:
            application.add_middleware(
                CORSMiddleware,
                allow_origins=settings.all_cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        application.include_router(api_router, prefix=settings.API_V1_STR)
    return application


app = create_app(include_legacy=settings.LEGACY_API_ENABLED)
