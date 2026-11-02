export type NavIcon = 'discover' | 'activity' | 'add' | 'records' | 'profile';

export interface NavItem {
	href: string;
	label: string;
	icon: NavIcon;
	/** Requires an account; anonymous visitors are sent to sign-in. */
	private: boolean;
}

/** Compact phone navigation from docs/product/mobile-journeys.md. */
export const PRIMARY_NAV: readonly NavItem[] = [
	{ href: '/', label: 'Discover', icon: 'discover', private: false },
	{ href: '/activity', label: 'Activity', icon: 'activity', private: true },
	{ href: '/jumps/new', label: 'Add jump', icon: 'add', private: true },
	{ href: '/records', label: 'Records', icon: 'records', private: true },
	{ href: '/profile', label: 'Profile', icon: 'profile', private: true }
];

export function isCurrent(href: string, pathname: string): boolean {
	if (href === '/') return pathname === '/';
	return pathname === href || pathname.startsWith(`${href}/`);
}
