import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV, isCurrent } from './navigation.ts';

describe('primary navigation', () => {
	it('matches the selected compact phone navigation order', () => {
		expect(PRIMARY_NAV.map((item) => item.label)).toEqual([
			'Discover',
			'Activity',
			'Add jump',
			'Records',
			'Profile'
		]);
		expect(PRIMARY_NAV.filter((item) => !item.private).map((item) => item.href)).toEqual(['/']);
	});

	it('marks the current section', () => {
		expect(isCurrent('/', '/')).toBe(true);
		expect(isCurrent('/', '/status')).toBe(false);
		expect(isCurrent('/records', '/records/gear')).toBe(true);
		expect(isCurrent('/records', '/recordsx')).toBe(false);
	});
});
