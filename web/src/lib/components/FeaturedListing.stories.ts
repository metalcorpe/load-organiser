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
					'The navy card: the next multi-day boogie or camp on the plain first page of the board, labelled only with what that selection knows ("Upcoming boogie"). It shows the full date range with the year and is not repeated in the dated list below it. One brand card per screen; orange only for the key number.'
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

export const AcrossMonths: Story = {
	args: { item: listing({ title: 'Summer boogie', starts_on: '2027-06-28', ends_on: '2027-07-03' }) }
};

export const AcrossYears: Story = {
	args: { item: listing({ title: 'New Year boogie', starts_on: '2027-12-30', ends_on: '2028-01-02' }) }
};
