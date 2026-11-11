import type { Meta, StoryObj } from '@storybook/sveltekit';
import PrivacyLabel from './PrivacyLabel.svelte';

const meta = {
	title: 'Navigation/Privacy label',
	component: PrivacyLabel,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'Who can see a page’s content. Private records say “only you”; a jump with a shared summary names that audience, so the label never hides a shared copy.'
			}
		}
	}
} satisfies Meta<typeof PrivacyLabel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Private: Story = {};
export const Logbook: Story = { args: { text: 'Private logbook — only you can see your jumps' } };
export const SharedWithFollowers: Story = {
	args: { text: 'Private entry — a summary is shared with approved followers' }
};
