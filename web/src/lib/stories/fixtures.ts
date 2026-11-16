import type { OpportunityOut } from '#lib/contracts/index.ts';

/** A listing for stories: real-looking dev data, every field set; override what a story needs. */
export function listing(overrides: Partial<OpportunityOut> = {}): OpportunityOut {
	return {
		id: '00000000-0000-4000-8000-000000000001',
		title: 'Christmas Boogie 2026',
		category: 'boogie',
		status: 'published',
		ended: false,
		provider: {
			id: '00000000-0000-4000-8000-000000000002',
			name: 'Skydive Empuriabrava',
			kind: 'organization'
		},
		venue: {
			id: '00000000-0000-4000-8000-000000000003',
			name: 'Skydive Empuriabrava',
			country: 'ES',
			locality: 'Empuriabrava',
			closed: false
		},
		country: 'ES',
		location_note: null,
		starts_on: '2026-12-24',
		ends_on: '2026-12-31',
		time_zone: 'Europe/Madrid',
		disciplines: ['belly', 'freefly', 'wingsuit'],
		audience: ['licensed'],
		languages: [],
		summary: 'Load organisers for FS, freefly and wingsuit, beach and balloon jumps.',
		prerequisites: null,
		price_amount: '80',
		price_currency: 'EUR',
		price_basis: 'per_person',
		price_tiers: [],
		price_note: null,
		registration_url: 'https://example.org/register',
		source_url: 'https://example.org/boogie',
		checked_on: '2026-11-09',
		...overrides
	};
}

/** The Christmas Boogie's price as dated tiers: €80 registration until 14 November, €95 after. */
const REGISTRATION = { label: 'Registration', currency: 'EUR', basis: 'per_person', optional: false } as const;
export const RISING_REGISTRATION: OpportunityOut['price_tiers'] = [
	{ ...REGISTRATION, amount: '80.00', from_on: null, until_on: '2026-11-14' },
	{ ...REGISTRATION, amount: '95.00', from_on: '2026-11-15', until_on: null },
	{
		label: 'Load organising',
		amount: '4.80',
		currency: 'EUR',
		basis: 'per_jump',
		from_on: null,
		until_on: null,
		optional: true
	}
];
