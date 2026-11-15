import type { Meta, StoryObj } from '@storybook/sveltekit';
import DestinationList from './DestinationList.svelte';

const meta = {
	title: 'Navigation/Destination list',
	component: DestinationList,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'Where things live, as grouped rows (the Me tab). Each row is one link of at least 52px, with an optional summary of what is there now. A setting ends in its verb ("Edit", the row’s one orange word); a place ends in a chevron. Supporting links (`quiet`) are plain links without a card. Groups sit side by side once the container is 44rem wide.'
			}
		}
	},
	args: {
		groups: [
			{
				id: 'plans',
				heading: 'Plans and gear',
				items: [
					{ href: '/plans', label: 'Plans and saved events', summary: '2 plans · 3 saved events' },
					{ href: '/gear', label: 'Gear', summary: 'Containers, canopies, AADs and service dates' }
				]
			},
			{
				id: 'preferences',
				heading: 'Profile and jump preferences',
				items: [
					{ href: '/profile/preferences#licence-heading', label: 'Licence', summary: 'B licence', verb: 'Edit' },
					{ href: '/profile/preferences#weight-heading', label: 'Exit weight', summary: 'Not set', verb: 'Edit' },
					{
						href: '/profile/public',
						label: 'Public profile',
						summary: '@averyveryverylonghandlewithoutbreaks · people can find you',
						verb: 'Edit'
					}
				]
			},
			{
				id: 'more',
				heading: 'More',
				quiet: true,
				items: [
					{ href: '/places', label: 'Private places' },
					{ href: '/privacy', label: 'Privacy and the beta' }
				]
			}
		]
	}
} satisfies Meta<typeof DestinationList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
