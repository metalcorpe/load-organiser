import { describe, expect, it } from 'vitest';
import { serverTimingHeader } from './server-timing.ts';

describe('serverTimingHeader', () => {
	it('lists each upstream call, then the session check and the total, in milliseconds', () => {
		expect(
			serverTimingHeader(
				[
					{ name: 'getSession', ms: 41.6 },
					{ name: 'listJumps', ms: 120.2 },
					{ name: 'getHistory', ms: 88 }
				],
				{ viewer: 42.1, total: 180.9 }
			)
		).toBe(
			'api-getSession;dur=41.6, api-listJumps;dur=120.2, api-getHistory;dur=88.0, viewer;dur=42.1, total;dur=180.9'
		);
	});

	it('numbers a call made twice, and keeps names to header-safe characters', () => {
		expect(
			serverTimingHeader(
				[
					{ name: 'listPlans', ms: 1 },
					{ name: 'listPlans', ms: 2 },
					{ name: 'bad name;dur=9', ms: 3 }
				],
				{ total: 10 }
			)
		).toBe('api-listPlans;dur=1.0, api-listPlans-2;dur=2.0, api-badnamedur9;dur=3.0, total;dur=10.0');
	});
});
