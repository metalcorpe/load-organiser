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
	{
		href: '/jumps',
		label: 'Logbook',
		icon: 'logbook',
		private: true,
		// Statistics is read from the logbook (History links to it), so it stays under Logbook.
		also: ['/history', '/stats']
	},
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
 * How a page sits on large screens (the layout rule, 2026-11-13). The header and the tabs are
 * the same on every page.
 *
 * - `frame`: the primary pages, Events and Dropzones (Explore), Logbook, Friends and Me. They
 *   share one centred frame as wide as the header, so each heading starts at the same left
 *   edge and nothing moves when switching tabs. Inside the frame a page uses columns
 *   (`.columns` in app.css: a main and a side column) or a grid of cards; paragraphs and forms
 *   keep their measure (`--measure`) and never run across the frame.
 * - `narrow`: every other page (sign-in and the other account pages, a listing's or a jump's
 *   own page, forms, settings, reading pages, and an error at any address) is one narrow
 *   column, centred.
 *
 * On phones every page is one column, the whole screen wide.
 */
export type PageLayout = 'frame' | 'narrow';

const FRAME_PAGES: readonly string[] = ['/', '/dz', '/jumps', '/activity', '/profile'];

export function pageLayout(pathname: string, error = false): PageLayout {
	return !error && FRAME_PAGES.includes(pathname) ? 'frame' : 'narrow';
}
