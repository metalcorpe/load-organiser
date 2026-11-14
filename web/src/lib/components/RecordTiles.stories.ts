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
					'Where a member’s own records live, grouped, as tiles with a line each on the Records page. Each tile is one tap target of at least 44px. Me lists the same places with DestinationList.'
			}
		}
	}
} satisfies Meta<typeof RecordTiles>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
