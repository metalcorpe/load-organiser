import { describe, expect, it } from 'vitest';
import { batchChanges, batchEcho, chosenIds, chosenVersions } from './jump-batch.ts';

const A = '0b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';
const B = '1b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';

function form(fields: Record<string, string | string[]>): FormData {
	const data = new FormData();
	for (const [name, value] of Object.entries(fields)) {
		for (const item of Array.isArray(value) ? value : [value]) data.append(name, item);
	}
	return data;
}

describe('chosen jumps', () => {
	it('keeps well-formed ids once', () => {
		expect(chosenIds(form({ id: [A, A.toUpperCase(), 'nope', B] }))).toEqual([A, B]);
	});

	it('reads id:version pairs and drops malformed ones', () => {
		expect(chosenVersions(form({ jump: [`${A}:3`, `${A}:4`, `${B}:0`, `${B}:x`, 'junk'] }))).toEqual([
			{ id: A, version: 3 }
		]);
	});
});

describe('batchChanges', () => {
	it('sends only what was chosen', () => {
		expect(batchChanges(form({ jump_type: 'freefly', at: '', aircraft: 'ignored' }))).toEqual({
			changes: { jump_type: 'freefly' },
			form: {
				jump_type: 'freefly',
				at: '',
				set_aircraft: false,
				aircraft: '',
				set_gear: false,
				component_ids: []
			}
		});
	});

	it('sets one place and clears the other kind', () => {
		const venue = batchChanges(form({ at: `venue:${A}` }));
		expect('changes' in venue && venue.changes).toEqual({ venue_id: A, place_id: null });
		const place = batchChanges(form({ at: `place:${B}` }));
		expect('changes' in place && place.changes).toEqual({ venue_id: null, place_id: B });
	});

	it('clears the aircraft or the gear only when asked', () => {
		const cleared = batchChanges(form({ set_aircraft: '1', aircraft: '  ', set_gear: '1' }));
		expect('changes' in cleared && cleared.changes).toEqual({ aircraft: null, component_ids: [] });
		const gear = batchChanges(form({ set_gear: '1', component_ids: [A, 'bad', A] }));
		expect('changes' in gear && gear.changes).toEqual({ component_ids: [A] });
	});

	it('refuses nothing chosen and malformed values', () => {
		expect(batchChanges(form({}))).toEqual({ error: 'nothing_to_change' });
		expect(batchChanges(form({ jump_type: 'skydance' }))).toEqual({ error: 'invalid_input' });
		expect(batchChanges(form({ at: 'venue:nope' }))).toEqual({ error: 'location_required' });
	});

	it('echoes what was typed after a refusal', () => {
		expect(batchEcho(form({ set_aircraft: '1', aircraft: 'Skyvan', component_ids: [B] }))).toEqual({
			jump_type: '',
			at: '',
			set_aircraft: true,
			aircraft: 'Skyvan',
			set_gear: false,
			component_ids: [B]
		});
	});
});
