import type { Meta, StoryObj } from '@storybook/sveltekit';
import { createRawSnippet } from 'svelte';
import Disclosure from './Disclosure.svelte';

const text = (html: string) => createRawSnippet(() => ({ render: () => html }));

const meta = {
	title: 'Forms/Disclosure',
	component: Disclosure,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'A folded group of optional fields (the jump form’s sections). Its initial state comes from the server, so it works without JavaScript; after that only the person opens or closes it. Folded fields are still part of the form and are sent.'
			}
		}
	},
	args: {
		summary: text('<span>Notes and links (optional, private)</span>'),
		children: text('<p>Fields of this section.</p>')
	}
} satisfies Meta<typeof Disclosure>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Closed: Story = {};
export const Open: Story = { args: { open: true } };
