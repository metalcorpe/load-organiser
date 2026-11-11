import type { Meta, StoryObj } from '@storybook/sveltekit';
import FeaturedListing from './FeaturedListing.svelte';
import { listing } from '#lib/stories/fixtures.ts';

const meta = {
	title: 'Listings/Featured card',
	component: FeaturedListing,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'The navy pop card: the next multi-day boogie or camp on the plain first page of the board. One brand card per screen; orange only for the key number.'
			}
		}
	},
	args: { item: listing() }
} satisfies Meta<typeof FeaturedListing>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Boogie: Story = {};

export const Camp: Story = {
	args: { item: listing({ category: 'camp', title: 'A-TEAM', starts_on: '2026-12-12', ends_on: '2026-12-13', price_amount: null }) }
};
