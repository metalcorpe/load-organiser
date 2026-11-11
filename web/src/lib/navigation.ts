export type NavIcon = 'events' | 'logbook' | 'friends' | 'me';

export interface NavItem {
	href: string;
	label: string;
	icon: NavIcon;
	/** Requires an account; anonymous visitors are sent to sign-in. */
	private: boolean;
	/** Other sections this tab stays highlighted for. */
	also: readonly string[];
}

/** Four tabs from design E (owner, 2026-11-11): logging lives in Logbook, records in Me. */
export const PRIMARY_NAV: readonly NavItem[] = [
	{ href: '/', label: 'Events', icon: 'events', private: false, also: ['/events'] },
	{ href: '/jumps', label: 'Logbook', icon: 'logbook', private: true, also: ['/history'] },
	{ href: '/activity', label: 'Friends', icon: 'friends', private: true, also: ['/people', '/posts'] },
	{
		href: '/profile',
		label: 'Me',
		icon: 'me',
		private: true,
		also: ['/records', '/gear', '/saved', '/plans', '/places', '/submit']
	}
];

function under(section: string, pathname: string): boolean {
	return pathname === section || pathname.startsWith(`${section}/`);
}

/** Whether a tab is the current one for this path. */
export function isCurrentTab(item: NavItem, pathname: string): boolean {
	if (item.href === '/') return pathname === '/' || item.also.some((s) => under(s, pathname));
	return [item.href, ...item.also].some((s) => under(s, pathname));
}

export function isCurrent(href: string, pathname: string): boolean {
	if (href === '/') return pathname === '/';
	return pathname === href || pathname.startsWith(`${href}/`);
}
