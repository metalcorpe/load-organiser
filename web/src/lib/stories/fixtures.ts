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
		price_note: '€95 from 15 Nov',
		registration_url: 'https://example.org/register',
		source_url: 'https://example.org/boogie',
		source_note: null,
		checked_on: '2026-11-09',
		...overrides
	};
}
