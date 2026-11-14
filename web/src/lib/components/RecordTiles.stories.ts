import type { Meta, StoryObj } from '@storybook/sveltekit';
import RecordTiles from './RecordTiles.svelte';

const meta = {
	title: 'Navigation/Record tiles',
	component: RecordTiles,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'Where a member’s own records live, grouped. Records shows tiles with a line each; the Me tab (profile) shows the same groups as compact link lists (`compact`), with its own groups added (`extra`). Each link is one tap target of at least 44px.'
			}
		}
	}
} satisfies Meta<typeof RecordTiles>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Compact: Story = {
	args: {
		compact: true,
		extra: [
			{
				id: 'account',
				heading: 'Account and settings',
				items: [
					{ href: '/profile/account', name: 'Account and security', text: '' },
					{ href: '#licence-heading', name: 'Licence', text: '' },
					{ href: '#weight-heading', name: 'Exit weight', text: '' }
				]
			}
		]
	}
};
