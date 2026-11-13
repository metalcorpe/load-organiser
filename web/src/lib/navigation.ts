export type NavIcon = 'explore' | 'logbook' | 'friends' | 'me';

export interface NavItem {
	href: string;
	label: string;
	icon: NavIcon;
	/** Requires an account; anonymous visitors are sent to sign-in. */
	private: boolean;
	/** Other sections this tab stays highlighted for. */
	also: readonly string[];
}

/**
 * Members' four tabs (design E, owner 2026-11-11). Guests get no tab bar: the public area is
 * Explore (Events | Dropzones), reached from the header and the Explore switch.
 */
export const PRIMARY_NAV: readonly NavItem[] = [
	{
		href: '/',
		label: 'Explore',
		icon: 'explore',
		private: false,
		also: ['/events', '/dz', '/organizers']
	},
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

/**
 * How far a page's header, tab bar, content and footer run on large screens. The discovery
 * lists use the room (Events most, for two columns of cards); forms, details and reading pages
 * keep a narrow measure, and so does an error page at any address. On phones every width
 * is the whole screen.
 */
export type PageWidth = 'narrow' | 'medium' | 'wide';

export function pageWidth(pathname: string, error = false): PageWidth {
	if (error) return 'narrow';
	if (pathname === '/') return 'wide';
	if (pathname === '/dz') return 'medium';
	return 'narrow';
}
