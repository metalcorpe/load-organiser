import type { Meta, StoryObj } from '@storybook/sveltekit';
import type { LicenceProgressOut } from '#lib/contracts/index.ts';
import LicenceProgress from './LicenceProgress.svelte';

const towardC: LicenceProgressOut = {
	licence: 'b',
	next_licence: 'c',
	jumps: 60,
	jumps_required: 200,
	jumps_include_prior: true,
	freefall_seconds: 2400,
	freefall_required_seconds: 3600,
	entries_with_freefall: 30,
	entries_without_freefall: 3,
	source: 'USPA SIM 3-1'
};

const meta = {
	title: 'Records/Licence progress',
	component: LicenceProgress,
	tags: ['autodocs'],
	args: { progress: towardC },
	parameters: {
		docs: {
			description: {
				component:
					'Jumps and recorded freefall time toward the next USPA licence (USPA SIM 3-1), from the jumper’s own entries. Other requirements are checked by USPA and instructors, not by the app. Shown on History beside the currency status.'
			}
		}
	}
} satisfies Meta<typeof LicenceProgress>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TowardC: Story = {};

export const StudentTowardA: Story = {
	args: {
		progress: {
			...towardC,
			licence: 'student',
			next_licence: 'a',
			jumps: 12,
			jumps_required: 25,
			jumps_include_prior: false,
			freefall_required_seconds: null,
			entries_without_freefall: 0
		}
	}
};

export const HighestLicence: Story = {
	args: {
		progress: { ...towardC, licence: 'd', next_licence: null, jumps_required: null, freefall_required_seconds: null }
	}
};
