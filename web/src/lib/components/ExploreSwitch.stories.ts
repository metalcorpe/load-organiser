import type { Meta, StoryObj } from '@storybook/sveltekit';
import ExploreSwitch from './ExploreSwitch.svelte';

const at = (path: string) => ({
	sveltekit_experimental: { state: { page: { url: new URL(`http://localhost${path}`) } } }
});

const meta = {
	title: 'Navigation/Explore switch',
	component: ExploreSwitch,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'The public area’s two views, Events and Dropzones, for guests and members alike. Plain links with aria-current, so each view keeps its own address and history.'
			}
		}
	}
} satisfies Meta<typeof ExploreSwitch>;

export default meta;
type Story = StoryObj<typeof meta>;

export const OnEvents: Story = { parameters: at('/') };
export const OnDropzones: Story = { parameters: at('/dz') };
