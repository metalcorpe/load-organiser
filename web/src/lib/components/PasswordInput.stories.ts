import type { Meta, StoryObj } from '@storybook/sveltekit';
import PasswordInput from './PasswordInput.svelte';

const meta = {
	title: 'Forms/Password input',
	component: PasswordInput,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component:
					'A password field with a Show/Hide button (registration, the sign-in page and the sign-in sheet). The button appears only with JavaScript and names its field for screen readers ("Show password"). Showing changes only the input type; name and autocomplete stay, so password managers keep working. The password is hidden again when the form is sent. Give it a <label for> with the same id, as on the pages.'
			}
		}
	},
	args: { id: 'story-password', name: 'password', autocomplete: 'current-password' }
} satisfies Meta<typeof PasswordInput>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SignIn: Story = {};

export const NewPassword: Story = {
	args: {
		id: 'story-new-password',
		autocomplete: 'new-password',
		minlength: 15,
		maxlength: 128
	}
};

export const RepeatedPassword: Story = {
	args: {
		id: 'story-repeat',
		name: 'password_confirm',
		autocomplete: 'new-password',
		what: 'repeated password'
	}
};

export const Invalid: Story = { args: { id: 'story-invalid', invalid: true } };
