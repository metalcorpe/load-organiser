import type { Meta, StoryObj } from '@storybook/sveltekit';
import ListingItem from './ListingItem.svelte';
import { listing } from '#lib/stories/fixtures.ts';

const meta = {
	title: 'Listings/Listing card',
	component: ListingItem,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'A listing on the board, dropzone and organizer pages. The date tile carries the type tint; the tag repeats the type with its own icon, so colour is never the only cue. The title link covers the card.'
			}
		}
	},
	args: { item: listing() }
} satisfies Meta<typeof ListingItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Boogie: Story = {};

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
