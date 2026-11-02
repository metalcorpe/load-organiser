import { defineConfig } from '@hey-api/openapi-ts';

// Types only: the transport is our own server-only native fetch adapter.
// Input is the beta-only contract exported by backend `app.skydiver.openapi`.
export default defineConfig({
	input: './contracts/skydiver-v1.openapi.json',
	output: { path: './src/lib/contracts/generated' },
	plugins: ['@hey-api/typescript']
});
