import type { Meta, StoryObj } from '@storybook/sveltekit';
import BarTable from './BarTable.svelte';

const meta = {
	title: 'Records/Bar table',
	component: BarTable,
	tags: ['autodocs'],
	args: {
		caption: 'Jumps by type',
		rowHeader: 'Type',
		valueHeader: 'Jumps',
		rows: [
			{ label: 'Freefly', value: 42 },
			{ label: 'Belly', value: 31 },
			{ label: 'Hop and pop', value: 4 }
		]
	},
	parameters: {
		docs: {
			description: {
				component:
					'A bar chart that is a data table: the numbers are the data, the bars are decorative and hidden from screen readers. Used on History and Statistics.'
			}
		}
	}
} satisfies Meta<typeof BarTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Counts: Story = {};

export const WingLoadingByMonth: Story = {
	args: {
		caption: 'Highest wing loading by month',
		rowHeader: 'Month',
		valueHeader: 'Highest',
		extraHeader: 'Jumps',
		rows: [
			{ label: 'Nov 2026', value: 1.2, text: '1.20', extra: '3' },
			{ label: 'Oct 2026', value: 1.06, text: '1.06', extra: '12' },
			{ label: 'Sep 2026', value: 0.95, text: '0.95', extra: '1' }
		],
		hint: 'Exit weight in pounds over the main canopy’s size in square feet.'
	}
};

export const WithEmptyRows: Story = {
	args: {
		caption: 'Jumps per month',
		rowHeader: 'Month',
		valueHeader: 'Jumps',
		rows: [
			{ label: 'Nov 2026', value: 5 },
			{ label: 'Oct 2026', value: 0 },
			{ label: 'Sep 2026', value: null }
		]
	}
};
