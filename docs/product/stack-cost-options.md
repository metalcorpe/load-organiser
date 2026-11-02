# Stack options for low operating costs

Status: historical discovery comparison, 2026-11-02. The subsequent [architecture decision](architecture.md) selects SvelteKit/Cloudflare Workers with FastAPI Cloud/Neon as the target to test; no migration or deployment is implemented. The funding objective is operating-expense coverage plus contingency, without initial personal income. No workload benchmark, deployment compatibility test, or total-cost estimate has been performed.

## Main distinction

Framework choice alone does not determine hosting cost. Where computation runs, what is stored, how often services are called, how data is backed up, and whether resources idle matter more. Changing React to another UI framework does not inherently remove backend, storage, or integration expenses.

The repository uses React/Vite, FastAPI, SQLModel/Alembic, and PostgreSQL. FastAPI itself does not require an always-on server, but the current Docker/deployment model is a conventional application process. A serverless runtime can require changes beyond packaging.

## Options

| Option | Potential operating benefit | Trade-off / migration |
| --- | --- | --- |
| Keep current stack on bounded/free hosting | Reuse code and relational design; potentially zero initial hosting invoices within provider allowances | Sleeping/limited resources, backup needs, account terms, and current app defects remain; free tiers are not guaranteed forever |
| Keep FastAPI; evaluate FastAPI Cloud Hobby | Official FastAPI-team hosting with a no-card free plan and scale-to-zero; avoids an immediate backend-language rewrite | Public beta, small shared resources, external database/storage budgets, deployment/migration testing, and future usage-billing changes |
| Keep React; use a small TypeScript Workers API and D1 | Request-based compute and managed SQL; no app server to administer | Backend, database/migrations, authentication integration, and data-access work; D1 uses SQLite semantics, not PostgreSQL |
| Keep Python; investigate FastAPI on Python Workers | Could retain some Python API/domain work while using serverless compute | Runtime/package/database compatibility audit required; existing psycopg, bcrypt, SQLModel, email, and migrations are not proven compatible as a set |
| Local-first personal app with a small shared service | Local logbook/gear editing and file analysis can reduce cloud processing/storage | Browser durability, backups, multi-device sync, conflict resolution, account recovery, and sharing add design work; not a drop-in stack replacement |

These approaches can be combined. Local processing can complement either backend. A switch to TypeScript does not automatically save more than adapting Python; compare a representative workflow and maintenance burden before choosing.

The [mobile direction](mobile-strategy.md) is a mobile-friendly responsive website. The owner selected SvelteKit/TypeScript for the planned frontend; React remains the current implementation. PWA installation/offline capabilities and native packaging are later options. Mobile distribution and server hosting are separate decisions; a native client does not eliminate backend costs.

## What can stay local, and what needs authority

Candidate local work: previewing imports, parsing supported tracks, computing personal charts, drafting log entries, and preparing exports. Large jobs can be processed in a browser worker where feasible; actual mobile memory/performance needs testing.

Shared services are still needed for authenticated cross-device synchronization, public listing moderation, issuer credentials, attributable signatures, conflicting gear claims, mutually confirmed transfers, and real bookings. Weather adapters may also need shared caching and secret/API protection. Local edits cannot promise live inventory, current issuer data, or another person's confirmation.

Browser storage is not a backup. The [browser storage documentation](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria) describes quotas, persistence, and eviction. A local-first design needs explicit export/restore, storage-status visibility, and an agreed recovery/sync strategy before inviting people to rely on it for their only logbook copy.

## Verified provider references

- [FastAPI Cloud](https://fastapi.tiangolo.com/deployment/fastapicloud/) is a separate service from Cloudflare Python Workers. Its [pricing](https://fastapicloud.com/pricing/) lists Hobby at $0 without a card, three apps, one seat, scale-to-zero, and short log retention. Pro is listed at $20/seat/month during public beta. [Usage documentation](https://fastapicloud.com/docs/team-management/billing/usage-based-billing/) identifies resource charges as planned and not invoiced during beta; future allowances must not be mistaken for permanently unlimited free compute. Evaluate external PostgreSQL, migrations, secrets, frontend hosting, and restore procedures separately. No deployment has been tested here.

- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) describes request-based Free/Paid compute and CPU limits. The free CPU budget makes expensive parsing, password operations, and analysis candidates for explicit testing, not assumed fits.
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) describes usage/storage quotas and limit behavior; [D1 overview](https://developers.cloudflare.com/d1/) identifies SQLite semantics. Free capacity is not unlimited service.
- [FastAPI on Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/) documents ASGI support; [package support](https://developers.cloudflare.com/workers/languages/python/packages/) describes supported Python/WebAssembly packages. This does not establish compatibility with the repository's full dependencies or PostgreSQL connection path.
- Earlier hosting research found free options for a prototype using [Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/), [Render](https://render.com/docs/free), and [Neon](https://neon.com/pricing). Deployment remains untested. Render free services sleep, have ephemeral local files, and are positioned for testing/hobby use; its free Postgres expires, so do not mistake it for durable free production storage.

Provider terms and quotas were researched, not provisioned. Verify current account/payment requirements and disable unbudgeted usage before deployment. No estimate of supported user counts is justified from request allowances alone.

## Proposed decision approach

1. Plan the selected SvelteKit/TypeScript frontend transition while retaining FastAPI/PostgreSQL; do not assume the framework change itself reduces hosting costs.
2. Document browser-side import/debrief processing, external media links, shared weather caching, bounded uploads, and record/export recovery as cost-control choices.
3. Select representative personal-record and shared-listing flows for a later comparison; no implementation is currently authorized by this discovery document.
4. Compare retaining FastAPI/PostgreSQL with serverless alternatives using measured latency, memory/CPU, storage, database operations, backup/restore, development effort, and projected invoices under explicit usage assumptions.
5. Choose limits and migration/export paths before introducing paid capacity. Treat maintenance and provider dependency as costs even when the hosting invoice is zero.

Current recommendation: reduce expensive workloads and evaluate serverless hosting before committing to a rewrite. The prototype has substantial missing personal-ecosystem functionality, so preserving every operational implementation detail is not automatically the cheapest long-term decision either.

The product owner selected Svelte. The [frontend transition document](svelte-transition.md) records SvelteKit/TypeScript with FastAPI/PostgreSQL, requiring UI/routing/auth integration work. Hosting savings are unmeasured and migration is not yet implemented. This decision supersedes the earlier React-retention recommendation.

FastAPI Cloud Hobby is a concrete candidate to test before considering a backend rewrite. This adds an option to the comparison; it is not an approval to deploy or a finding that it is the cheapest sustainable service.

Related: [sustainability](sustainability.md), [connected product model](product-model.md), and [implementation assessment](implementation-assessment.md).
