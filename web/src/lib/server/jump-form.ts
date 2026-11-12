/**
 * Jump form parsing for the private logbook (#153). The API is the authority on
 * every rule; this only turns form fields into the request body and refuses
 * malformed input before sending. Empty optional fields become null, never zero.
 */
import { isUuid } from './api/transport.ts';
import { field } from './forms.ts';
import { text } from './review-forms.ts';

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const TIME = /^\d{2}:\d{2}$/;

export type JumpBody = Record<string, unknown>;

function whole(data: FormData, name: string): number | null | 'invalid' {
	const raw = field(data, name, { max: 12, trim: true }).replace(/[\s,]/g, '');
	if (!raw) return null;
	return /^\d+$/.test(raw) ? Number(raw) : 'invalid';
}

/** The jump fields, or an error code when the form itself is malformed. */
export function jumpBody(data: FormData): { body: JumpBody } | { error: string } {
	const jumpedOn = field(data, 'jumped_on', { max: 10 });
	const jumpType = field(data, 'jump_type', { max: 16 });
	if (!DATE.test(jumpedOn) || !jumpType) return { error: 'missing' };

	const venue = field(data, 'venue_id', { max: 64 });
	const place = field(data, 'place_id', { max: 64 });
	if (!(isUuid(venue) ? !place : isUuid(place) && !venue)) return { error: 'location_required' };

	const numbers: Record<string, number | null> = {};
	for (const name of ['jump_number', 'exit_altitude', 'deployment_altitude', 'freefall_seconds']) {
		const value = whole(data, name);
		if (value === 'invalid') return { error: 'invalid_input' };
		numbers[name] = value;
	}
	const hasAltitude = numbers.exit_altitude !== null || numbers.deployment_altitude !== null;

	const exitTime = field(data, 'exit_time', { max: 8 });
	if (exitTime && !TIME.test(exitTime)) return { error: 'exit_time_invalid' };

	const components = data
		.getAll('component_ids')
		.filter((v): v is string => typeof v === 'string')
		.filter((id) => isUuid(id))
		.slice(0, 20);
	const links = field(data, 'links', { max: 12_000 })
		.split(/\r?\n/)
		.map((line) => line.trim())
		.filter(Boolean);

	return {
		body: {
			jumped_on: jumpedOn,
			jump_type: jumpType,
			venue_id: isUuid(venue) ? venue : null,
			place_id: isUuid(place) ? place : null,
			jump_number: numbers.jump_number,
			// A time zone without a time means nothing: neither is sent.
			exit_time: exitTime || null,
			time_zone: exitTime ? text(data, 'time_zone', 64) : null,
			exit_altitude: numbers.exit_altitude,
			deployment_altitude: numbers.deployment_altitude,
			// Unit and datum only accompany an altitude; none is implied otherwise.
			altitude_unit: hasAltitude ? text(data, 'altitude_unit', 2) : null,
			altitude_datum: hasAltitude
				? (text(data, 'altitude_datum', 12) ?? 'unspecified')
				: 'unspecified',
			freefall_seconds: numbers.freefall_seconds,
			component_ids: components,
			other_gear: text(data, 'other_gear', 400),
			aircraft: text(data, 'aircraft', 120),
			notes: text(data, 'notes', 4000),
			links
		}
	};
}

/** The optional "new component used on this jump" branch, when filled in. */
export function newComponent(
	data: FormData
): { kind: string; label: string; clientKey: string } | null | 'invalid' {
	const label = field(data, 'new_component_label', { max: 200, trim: true });
	if (!label) return null;
	const clientKey = field(data, 'new_component_key', { max: 64 });
	const kind = field(data, 'new_component_kind', { max: 16 });
	if (!isUuid(clientKey) || !kind) return 'invalid';
	return { kind, label, clientKey };
}
