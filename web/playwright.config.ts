import { defineConfig, devices } from '@playwright/test';

// Exercises the production Cloudflare build in local workerd previews
// (`wrangler dev`), not the Vite dev server. Run through `npm run test:e2e`,
// which builds first. API origins are explicit; no .env file is loaded.
//   :4173 -> E2E_API_ORIGIN (an isolated FastAPI + disposable PostgreSQL)
//   :4174 -> a closed loopback port, to exercise the upstream-failure path
const apiOrigin = process.env.E2E_API_ORIGIN ?? 'http://127.0.0.1:8144';
const unreachableOrigin = 'http://127.0.0.1:9';

const preview = (port: number, origin: string, inspector: number) => ({
	command: `wrangler dev .svelte-kit/cloudflare/_worker.js --port ${port} --ip 127.0.0.1 --inspector-port ${inspector} --persist-to .wrangler/e2e-${port} --var API_ORIGIN:${origin}`,
	url: `http://127.0.0.1:${port}/`,
	reuseExistingServer: false,
	timeout: 120_000,
	env: { WRANGLER_SEND_METRICS: 'false' }
});

export default defineConfig({
	testDir: 'tests',
	testMatch: '**/*.e2e.ts',
	workers: 1,
	use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
	projects: [
		{ name: 'pixel-7', use: { ...devices['Pixel 7'] } },
		{
			name: 'chromium-320',
			use: { ...devices['Desktop Chrome'], viewport: { width: 320, height: 640 }, hasTouch: true }
		}
	],
	webServer: [preview(4173, apiOrigin, 9244), preview(4174, unreachableOrigin, 9245)]
});
