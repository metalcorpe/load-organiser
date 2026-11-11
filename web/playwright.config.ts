import { defineConfig, devices } from '@playwright/test';

// Exercises the production Cloudflare build in local workerd previews
// (`wrangler dev`), not the Vite dev server. Run through `npm run test:e2e`,
// which builds first. Origins and keys are explicit; no .env file is loaded.
//   :4173 http  -> E2E_API_ORIGIN (an isolated FastAPI + disposable PostgreSQL)
//   :4174 http  -> a closed loopback port, to exercise the upstream-failure path
//   :4175 https -> E2E_API_ORIGIN with the production __Host- Secure cookie (#145)
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
	// One browser at a time by default. Measured 2026-11-11: 4 workers were not faster on an
	// 8-core machine (previews, API and database compete for the same CPU) and exposed
	// timing assumptions in several tests. E2E_WORKERS=N to experiment.
	workers: Number(process.env.E2E_WORKERS) || 1,
	use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
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
		preview({ port: 4173, api: apiOrigin, inspector: 9244 }),
		preview({ port: 4174, api: unreachableOrigin, inspector: 9245 }),
		preview({ port: 4175, api: apiOrigin, inspector: 9246, https: true })
	]
});
