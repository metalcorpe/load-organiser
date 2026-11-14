/**
 * The three local previews the e2e tests run against (playwright.config.ts). Their ports follow
 * E2E_PORT_BASE (default 4173), so several isolated runs can use one machine at once
 * (scripts/verify.sh, E2E_STACKS): each run gets its own base.
 */
export const PORT_BASE = Number(process.env.E2E_PORT_BASE) || 4173;

/** Plain http, API at E2E_API_ORIGIN. */
export const PLAIN_PORT = PORT_BASE;
/** Plain http, API pointed at a closed port: the upstream-failure path. */
export const UNREACHABLE_PORT = PORT_BASE + 1;
/** https, API at E2E_API_ORIGIN, with the production __Host- Secure cookie (#145). */
export const SECURE_PORT = PORT_BASE + 2;

export const PLAIN_ORIGIN = `http://127.0.0.1:${PLAIN_PORT}`;
export const UNREACHABLE_ORIGIN = `http://127.0.0.1:${UNREACHABLE_PORT}`;
export const SECURE_ORIGIN = `https://127.0.0.1:${SECURE_PORT}`;
