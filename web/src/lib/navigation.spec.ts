import { describe, expect, it } from 'vitest';
import { PRIMARY_NAV, isCurrent, isCurrentTab, pageLayout } from './navigation.ts';

const tab = (label: string) => PRIMARY_NAV.find((item) => item.label === label)!;
const current = (pathname: string) =>
	PRIMARY_NAV.filter((item) => isCurrentTab(item, pathname)).map((item) => item.label);

describe('primary navigation', () => {
	it('has the four member tabs, only Explore public', () => {
		expect(PRIMARY_NAV.map((item) => item.label)).toEqual(['Explore', 'Logbook', 'Friends', 'Me']);
		expect(PRIMARY_NAV.filter((item) => !item.private).map((item) => item.href)).toEqual(['/']);
	});

	it('highlights exactly one tab for each section', () => {
		expect(current('/')).toEqual(['Explore']);
		expect(current('/events/abc')).toEqual(['Explore']);
		expect(current('/dz')).toEqual(['Explore']);
		expect(current('/dz/abc')).toEqual(['Explore']);
		expect(current('/organizers/abc')).toEqual(['Explore']);
		expect(current('/jumps')).toEqual(['Logbook']);
		expect(current('/jumps/new')).toEqual(['Logbook']);
		expect(current('/history/baseline')).toEqual(['Logbook']);
		expect(current('/stats')).toEqual(['Logbook']);
		expect(current('/statsx')).toEqual([]);
		expect(current('/activity')).toEqual(['Friends']);
		expect(current('/people/someone')).toEqual(['Friends']);
		expect(current('/gear/x')).toEqual(['Me']);
		expect(current('/records')).toEqual(['Me']);
		expect(current('/profile/data')).toEqual(['Me']);
		expect(current('/status')).toEqual([]);
		expect(current('/jumpsx')).toEqual([]);
		expect(isCurrentTab(tab('Explore'), '/dzx')).toBe(false);
	});

	it('keeps the plain section check', () => {
		expect(isCurrent('/records', '/records/gear')).toBe(true);
		expect(isCurrent('/records', '/recordsx')).toBe(false);
	});

	it('frames the primary pages and keeps every other page narrow', () => {
		for (const path of ['/', '/dz', '/jumps', '/activity', '/profile']) {
			expect(pageLayout(path)).toBe('frame');
		}
		for (const path of [
			'/dz/abc',
			'/events/abc',
			'/register',
			'/sign-in',
			'/jumps/new',
			'/jumps/abc/edit',
			'/profile/account',
			'/people',
			'/privacy',
			'/jumpsx'
		]) {
			expect(pageLayout(path)).toBe('narrow');
		}
		// An error page is narrow whatever its address.
		expect(pageLayout('/', true)).toBe('narrow');
		expect(pageLayout('/jumps', true)).toBe('narrow');
	});
});
