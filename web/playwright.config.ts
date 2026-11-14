import { defineConfig, devices } from '@playwright/test';
import { PLAIN_ORIGIN, PLAIN_PORT, SECURE_PORT, UNREACHABLE_PORT } from './tests/support/origins.ts';

// Exercises the production Cloudflare build in local workerd previews
// (`wrangler dev`), not the Vite dev server. Run through `npm run test:e2e`,
// which builds first. Origins and keys are explicit; no .env file is loaded.
// Ports from E2E_PORT_BASE (default 4173; tests/support/origins.ts):
//   base     http  -> E2E_API_ORIGIN (an isolated FastAPI + disposable PostgreSQL)
//   base + 1 http  -> a closed loopback port, to exercise the upstream-failure path
//   base + 2 https -> E2E_API_ORIGIN with the production __Host- Secure cookie (#145)
// Each preview's inspector listens on its port + 5071 (9244 to 9246 by default).
const apiOrigin = process.env.E2E_API_ORIGIN ?? 'http://127.0.0.1:8144';
const unreachableOrigin = 'http://127.0.0.1:9';
const proxyKey = process.env.E2E_API_PROXY_KEY ?? '';

interface Preview {
	port: number;
	api: string;
	inspector: number;
	https?: boolean;
}

const preview = ({ port, api, inspector, https = false }: Preview) => {
	const origin = `${https ? 'https' : 'http'}://127.0.0.1:${port}`;
	const vars = [`API_ORIGIN:${api}`, `APP_ORIGIN:${origin}`];
	if (https && proxyKey) vars.push(`API_PROXY_KEY:${proxyKey}`);
	return {
		command:
			`wrangler dev .svelte-kit/cloudflare/_worker.js --port ${port} --ip 127.0.0.1 ` +
			`--inspector-port ${inspector} --persist-to .wrangler/e2e-${port} ` +
			(https ? '--local-protocol https ' : '') +
			vars.map((v) => `--var ${v}`).join(' '),
		url: `${origin}/`,
		ignoreHTTPSErrors: https,
		reuseExistingServer: false,
		timeout: 120_000,
		env: { WRANGLER_SEND_METRICS: 'false' }
	};
};

export default defineConfig({
	testDir: 'tests',
	testMatch: '**/*.e2e.ts',
	// One browser at a time against one database and API. Measured 2026-11-11: 4 workers were
	// not faster on an 8-core machine and exposed timing assumptions in several tests (they
	// share one database). scripts/verify.sh runs shards side by side instead (E2E_STACKS),
	// each with its own database and API. E2E_WORKERS=N to experiment.
	workers: Number(process.env.E2E_WORKERS) || 1,
	// Separate per run, so shards running side by side do not clear each other's results.
	outputDir: process.env.E2E_OUTPUT_DIR || 'test-results',
	use: { baseURL: PLAIN_ORIGIN, trace: 'retain-on-failure' },
	projects: [
		{ name: 'pixel-7', use: { ...devices['Pixel 7'] } },
		// Mobile Safari's engine (WebKit) with iPhone viewport, touch and user agent.
		// An emulation, not a real device check (#160 records that separately).
		{ name: 'iphone-13', use: { ...devices['iPhone 13'] } },
		{
			name: 'chromium-320',
			use: { ...devices['Desktop Chrome'], viewport: { width: 320, height: 640 }, hasTouch: true }
		}
	],
	webServer: [
		preview({ port: PLAIN_PORT, api: apiOrigin, inspector: PLAIN_PORT + 5071 }),
		preview({ port: UNREACHABLE_PORT, api: unreachableOrigin, inspector: UNREACHABLE_PORT + 5071 }),
		preview({ port: SECURE_PORT, api: apiOrigin, inspector: SECURE_PORT + 5071, https: true })
	]
});
