import { describe, expect, it } from 'vitest';
import { jumpBody, newComponent } from './jump-form.ts';

const PLACE = '0b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';
const GEAR = '1b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';

function form(fields: Record<string, string | string[]>): FormData {
	const data = new FormData();
	for (const [key, value] of Object.entries(fields)) {
		for (const item of Array.isArray(value) ? value : [value]) data.append(key, item);
	}
	return data;
}

const BASE = { jumped_on: '2026-10-10', jump_type: 'belly', place_id: PLACE };

describe('jumpBody', () => {
	it('keeps empty optional fields null, never zero, and implies no unit or zone', () => {
		const parsed = jumpBody(form({ ...BASE, time_zone: 'Europe/Madrid', altitude_unit: 'ft' }));
		expect(parsed).toEqual({
			body: expect.objectContaining({
				venue_id: null,
				place_id: PLACE,
				jump_number: null,
				exit_time: null,
				time_zone: null,
				exit_altitude: null,
				altitude_unit: null,
				altitude_datum: 'unspecified',
				freefall_seconds: null,
				component_ids: [],
				links: []
			})
		});
	});

	it('passes entered values, full-length component ids and one link per line', () => {
		const parsed = jumpBody(
			form({
				...BASE,
				jump_number: '1,204',
				exit_time: '14:05',
				time_zone: 'Europe/Madrid',
				exit_altitude: '4000',
				altitude_unit: 'm',
				altitude_datum: 'agl',
				freefall_seconds: '0',
				component_ids: [GEAR, 'not-a-uuid'],
				links: 'https://a.example/1\r\n\r\n https://a.example/2 '
			})
		);
		expect(parsed).toEqual({
			body: expect.objectContaining({
				jump_number: 1204,
				exit_time: '14:05',
				time_zone: 'Europe/Madrid',
				exit_altitude: 4000,
				altitude_unit: 'm',
				altitude_datum: 'agl',
				freefall_seconds: 0,
				component_ids: [GEAR],
				links: ['https://a.example/1', 'https://a.example/2']
			})
		});
	});

	it('refuses a malformed form before sending', () => {
		expect(jumpBody(form({ ...BASE, jumped_on: '10/10/2026' }))).toEqual({ error: 'missing' });
		expect(jumpBody(form({ ...BASE, place_id: '' }))).toEqual({ error: 'location_required' });
		expect(jumpBody(form({ ...BASE, venue_id: GEAR }))).toEqual({ error: 'location_required' });
		expect(jumpBody(form({ ...BASE, exit_altitude: '-5' }))).toEqual({ error: 'invalid_input' });
		expect(jumpBody(form({ ...BASE, exit_time: '9am' }))).toEqual({ error: 'exit_time_invalid' });
	});
});

describe('newComponent', () => {
	it('is skipped without a label and needs its own key', () => {
		expect(newComponent(form({ new_component_kind: 'main' }))).toBeNull();
		expect(
			newComponent(
				form({ new_component_label: 'Sabre', new_component_kind: 'main', new_component_key: 'x' })
			)
		).toBe('invalid');
		expect(
			newComponent(
				form({
					new_component_label: ' Sabre ',
					new_component_kind: 'main',
					new_component_key: GEAR
				})
			)
		).toEqual({ kind: 'main', label: 'Sabre', clientKey: GEAR });
	});
});
