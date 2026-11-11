import type { Meta, StoryObj } from '@storybook/sveltekit';
import TypeIcon from './TypeIcon.svelte';

const meta = {
	title: 'Listings/Type icon',
	component: TypeIcon,
	tags: ['autodocs'],
	argTypes: {
		category: { control: 'select', options: ['boogie', 'camp', 'course', 'event'] },
		size: { control: { type: 'range', min: 12, max: 48 } }
	},
	args: { category: 'boogie', size: 32 }
} satisfies Meta<typeof TypeIcon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Boogie: Story = {};
export const Camp: Story = { args: { category: 'camp' } };
export const Course: Story = { args: { category: 'course' } };
export const Event: Story = { args: { category: 'event' } };
