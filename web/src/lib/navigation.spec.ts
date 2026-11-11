import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV, isCurrent, isCurrentTab } from './navigation.ts';

const tab = (label: string) => PRIMARY_NAV.find((item) => item.label === label)!;
const current = (pathname: string) =>
	PRIMARY_NAV.filter((item) => isCurrentTab(item, pathname)).map((item) => item.label);

describe('primary navigation', () => {
	it('has the four tabs of design E, only Events public', () => {
		expect(PRIMARY_NAV.map((item) => item.label)).toEqual(['Events', 'Logbook', 'Friends', 'Me']);
		expect(PRIMARY_NAV.filter((item) => !item.private).map((item) => item.href)).toEqual(['/']);
	});

	it('highlights exactly one tab for each section', () => {
		expect(current('/')).toEqual(['Events']);
		expect(current('/events/abc')).toEqual(['Events']);
		expect(current('/jumps')).toEqual(['Logbook']);
		expect(current('/jumps/new')).toEqual(['Logbook']);
		expect(current('/history/baseline')).toEqual(['Logbook']);
		expect(current('/activity')).toEqual(['Friends']);
		expect(current('/people/someone')).toEqual(['Friends']);
		expect(current('/gear/x')).toEqual(['Me']);
		expect(current('/records')).toEqual(['Me']);
		expect(current('/profile/data')).toEqual(['Me']);
		expect(current('/status')).toEqual([]);
		expect(current('/jumpsx')).toEqual([]);
		expect(isCurrentTab(tab('Events'), '/dz')).toBe(false);
	});

	it('keeps the plain section check', () => {
		expect(isCurrent('/records', '/records/gear')).toBe(true);
		expect(isCurrent('/records', '/recordsx')).toBe(false);
	});
});
