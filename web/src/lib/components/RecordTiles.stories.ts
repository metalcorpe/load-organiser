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
					'Where a member’s own records live, grouped. Shown on the Me tab (profile) and on Records. Each tile is one tap target.'
			}
		}
	}
} satisfies Meta<typeof RecordTiles>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
