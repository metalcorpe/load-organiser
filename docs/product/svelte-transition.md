# React to Svelte transition

Status: selected frontend direction following the product owner's explicit Svelte preference. Use SvelteKit with TypeScript for the planned responsive website, retaining FastAPI and PostgreSQL. Migration execution and release scope are separate work; no dependency installation or application code change has been performed.

## Recommendation

SvelteKit with TypeScript is the selected frontend direction while keeping FastAPI and PostgreSQL. This is a frontend replacement, not a reason to duplicate business rules in a second backend. The early prototype has substantial unimplemented skydiver-facing scope; migrate the foundation before building those screens. The [architecture decisions](architecture.md) now select SSR, scoped CSS/native controls, backend sessions through a same-origin cookie boundary, and the Cloudflare adapter. Those decisions still require implementation and runtime testing.

Do not justify migration with unmeasured hosting or performance savings. Both frontends can use static hosting. Benefits depend on team familiarity, implementation quality, route rendering, and maintenance effort.

## Repository impact

| Existing element | Treatment |
| --- | --- |
| FastAPI routes, SQLModel models, PostgreSQL, migrations | Remain backend responsibilities; known defects are not solved by changing frontend |
| Generated TypeScript API types and Axios client in `frontend/src/client` | Regenerate public-safe contract types; use server-only request-local native fetch in the Workers frontend, not the legacy mutable client |
| Pure TypeScript utilities | Technically portable where framework-independent; do not endorse current optimization rules merely by copying them |
| React/TSX pages and components | Rewrite as Svelte components; not automatic syntax conversion |
| Chakra UI and Emotion | Replace with Svelte-compatible components or scoped styles and accessible primitives |
| TanStack React Router and generated route tree | Replace with SvelteKit routes/layouts |
| React Query/hooks, React Hook Form, theme/icons/providers | Replace/adapt with Svelte-compatible state, data-fetching, forms, styling, and icons |
| Existing Playwright tests | Preserve meaningful scenarios; update selectors, server/build setup, and framework assumptions |
| Vite/build, Docker/nginx, deployment configuration | Adapt output paths, route fallback, env handling, build dependencies, and target adapter |

The current frontend is primarily a staff dashboard rather than the proposed social/discovery product. Distinguish a behavior-preserving migration of existing routes from building new V1 features. The [handoff route inventory](claude-code-handoff.md) explicitly excludes unsupported operational routes from the beta router, while retaining their code/tables for reference.

## Rendering and hosting

Selected decision: public SSR, authenticated server loads, static help only, Cloudflare Workers adapter, and no-store for dynamic data. FastAPI Cloud Hobby/Neon Free are the backend/database targets to test. The alternatives below explain the comparison; they do not reopen the selection.

SvelteKit offers routing and selectable rendering/deployment modes. [Static output](https://svelte.dev/docs/kit/adapter-static) can preserve a separate statically hosted frontend and FastAPI API. Client-rendered protected routes can use an appropriate fallback, but [SPA-only rendering](https://svelte.dev/docs/kit/single-page-apps) has discovery/performance trade-offs; don't disable SSR globally without considering public pages.

Public DZ, event, and permitted activity pages may benefit from prerendered or server-rendered HTML and share metadata. Prerendering needs a known route set and refresh/rebuild plan; changing database content does not magically update built pages. Dynamic server rendering needs a compatible runtime and explicit private-cache boundaries. [Cloudflare adapter](https://svelte.dev/docs/kit/adapter-cloudflare) is one deployment option, not a tested configuration.

FastAPI Cloud remains a backend-hosting candidate. Choosing SvelteKit does not establish where any SvelteKit server rendering runs or imply that frontend server code is hosted on FastAPI Cloud automatically.

## Authentication and data boundaries

The current app reads a bearer token from browser localStorage. That code cannot simply run during server rendering. Use the selected opaque backend session and same-origin HttpOnly cookie arrangement from architecture A4–A5. Do not put user-specific tokens in a shared module/global client when serving multiple users.

Public pages must not receive private logbook/gear data through server loads, hydration payloads, generated files, or shared caches. Backend permissions continue to protect records. Shared-card visibility, follows, unpublishing, and blocking need the same server-side enforcement regardless of frontend.

## Proposed migration sequence

1. Record route/feature parity and the rendering/auth/deployment decisions; retain the current app as a rollback/reference while the replacement is incomplete.
2. Establish SvelteKit/TypeScript, a mobile layout, API access, environment handling, and one end-to-end authenticated flow.
3. Verify login, logout, expiry/error handling, deep links, and public-versus-private isolation before porting more screens.
4. Port supported existing behavior explicitly; build missing discovery/social/logbook/gear capabilities as separately scoped features, not assumed migration output.
5. Update and run meaningful route/API/browser checks; build for the intended hosting adapter and test direct navigation and responsive behavior.
6. Remove React-specific code/dependencies only when agreed supported behavior is covered and the replacement is verified. Review deployment and recovery instructions at cutover.

No migration effort estimate or parity guarantee has been established. A later implementation should use a separate feature branch and preserve the existing documentation changes.

Sources: [Svelte overview](https://svelte.dev/docs/svelte/overview), [SvelteKit introduction](https://svelte.dev/docs/kit/introduction), and the adapter/rendering documentation linked above. Compatibility, build size, accessibility, and mobile performance remain untested.
