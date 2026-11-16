import type { Meta, StoryObj } from '@storybook/sveltekit';
import ListingItem from './ListingItem.svelte';
import { listing, RISING_REGISTRATION } from '#lib/stories/fixtures.ts';

const meta = {
	title: 'Listings/Listing card',
	component: ListingItem,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'A listing on the board, dropzone and organizer pages. The date tile carries the type tint and the start; a listing of several days also shows its start and finish beside the type (both years across a new year). The tag repeats the type with its own icon, so colour is never the only cue. The title link covers the card.'
			}
		}
	},
	args: { item: listing() }
} satisfies Meta<typeof ListingItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Boogie: Story = {};

export const PriceByDate: Story = {
	name: 'Price that changes by date',
	parameters: {
		docs: {
			description: {
				story:
					'Dated tiers: the card shows only the required tier in effect today in the listing\'s time zone, with its label. An expired tier is never shown; with no single tier in effect it says "See pricing".'
			}
		}
	},
	args: {
		item: listing({
			price_amount: null,
			price_currency: null,
			price_basis: null,
			price_tiers: RISING_REGISTRATION
		})
	}
};

export const OneDay: Story = {
	name: 'One day',
	args: { item: listing({ title: 'Sunday fun jumps', starts_on: '2026-12-13', ends_on: '2026-12-13' }) }
};

export const AcrossANewYear: Story = {
	name: 'Across a new year',
	args: { item: listing({ title: 'New Year boogie', starts_on: '2027-12-30', ends_on: '2028-01-02' }) }
};

export const Camp: Story = {
	args: {
		item: listing({ category: 'camp', title: 'A-TEAM', starts_on: '2026-12-12', ends_on: '2026-12-13', price_amount: null })
	}
};

export const Course: Story = {
	args: {
		item: listing({
			category: 'course',
			title: 'Curso de Campana Marcos',
			starts_on: '2026-11-14',
			ends_on: '2026-11-14',
			price_amount: null,
			venue: { id: 'v', name: 'Skydive Madrid (Aeródromo de Lillo)', country: 'ES', locality: 'Lillo', closed: false },
			provider: { id: 'p', name: 'Skydive Madrid', kind: 'organization' }
		})
	}
};

export const Event: Story = {
	args: { item: listing({ category: 'event', title: 'LET event', starts_on: '2026-11-14', ends_on: '2026-11-14', price_amount: null }) }
};

export const UndatedGreekTitle: Story = {
	name: 'Undated, Greek title',
	args: {
		item: listing({
			category: 'course',
			title: 'Εκπαίδευση AFF',
			status: 'postponed',
			starts_on: null,
			ends_on: null,
			country: 'GR',
			price_amount: null,
			venue: { id: 'v', name: 'Mesolongi Civil Airfield (Πολιτικό Αεροδρόμιο Μεσολογγίου)', country: 'GR', locality: 'Mesolongi', closed: false },
			provider: { id: 'p', name: 'Skydive Athens', kind: 'organization' }
		})
	}
};

export const Cancelled: Story = {
	args: { item: listing({ status: 'cancelled' }) }
};

export const Ended: Story = {
	args: { item: listing({ ended: true }) }
};

/** On the board after a search: the link carries the search, for "Back to results". */
export const InSearchResults: Story = {
	args: { results: '/?country=ES&from=2026-12-01' }
};
