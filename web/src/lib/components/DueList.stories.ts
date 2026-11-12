import type { Meta, StoryObj } from '@storybook/sveltekit';
import type { GearDueOut } from '#lib/contracts/index.ts';
import DueList from './DueList.svelte';

const reserve = { id: '00000000-0000-4000-8000-000000000011', kind: 'reserve' as const, label: 'PD 160 reserve' };
const aad = { id: '00000000-0000-4000-8000-000000000012', kind: 'aad' as const, label: 'Cypres 2' };

const items: GearDueOut[] = [
	{
		component: aad,
		kind: 'service',
		service_kind: 'aad_service',
		due_on: '2026-11-02',
		basis: 'entered',
		interval_days: null,
		interval_source: null,
		status: 'overdue'
	},
	{
		component: reserve,
		kind: 'reserve_repack',
		service_kind: 'repack',
		due_on: '2026-11-17',
		basis: 'interval',
		interval_days: 180,
		interval_source: 'USPA / FAA 14 CFR 105.43',
		status: 'soon'
	},
	{
		component: { id: '00000000-0000-4000-8000-000000000013', kind: 'main', label: 'Sabre 170' },
		kind: 'jump_limit',
		service_kind: 'maintenance',
		due_on: null,
		basis: 'entered',
		interval_days: null,
		interval_source: null,
		status: 'soon',
		label: 'Reline',
		jump_limit: 500,
		jumps_used: 488,
		jumps_left: 12,
		counted_since: '2025-06-01'
	},
	{
		component: aad,
		kind: 'end_of_life',
		service_kind: null,
		due_on: '2034-04-01',
		basis: 'entered',
		interval_days: null,
		interval_source: null,
		status: 'later'
	}
];

const meta = {
	title: 'Records/Due list',
	component: DueList,
	tags: ['autodocs'],
	args: { items: items.slice(0, 3), today: '2026-11-12', label: 'Due soon' },
	parameters: {
		docs: {
			description: {
				component:
					'Dates coming due on the owner’s own gear, each linked to its component. Compact on the Logbook (due within 30 days or overdue); with where each date comes from on the Gear page.'
			}
		}
	}
} satisfies Meta<typeof DueList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Compact: Story = {};

export const Detailed: Story = {
	args: { items, label: 'Due dates', detailed: true }
};
