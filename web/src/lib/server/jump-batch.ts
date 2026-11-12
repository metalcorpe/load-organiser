/**
 * Form parsing for changing many jumps at once (/jumps "Select" mode). The API is the
 * authority on every rule; this only turns form fields into request bodies and
 * refuses malformed input before sending. Nothing here is per-item I/O.
 */
import { JUMP_TYPE_LABEL } from '#lib/jumps.ts';
import { isUuid } from './api/transport.ts';
import { field } from './forms.ts';
import { text } from './review-forms.ts';

/** More than the API's 200, so a larger choice gets the API's own explanation. */
const IDS_MAX = 400;
const AT = /^(venue|place):([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/;

/** The choices as sent, to carry from the check to the confirmation unchanged. */
export interface BatchForm {
	jump_type: string;
	at: string;
	set_aircraft: boolean;
	aircraft: string;
	set_gear: boolean;
	component_ids: string[];
}

export type BatchChanges = Record<string, unknown>;

function uuids(data: FormData, name: string, max: number): string[] {
	const found = data
		.getAll(name)
		.filter((v): v is string => typeof v === 'string')
		.map((v) => v.toLowerCase())
		.filter((v) => isUuid(v));
	return [...new Set(found)].slice(0, max);
}

/** The ticked jumps. */
export function chosenIds(data: FormData): string[] {
	return uuids(data, 'id', IDS_MAX);
}

/** `id:version` pairs carried from the check to the confirmation. */
export function chosenVersions(data: FormData): { id: string; version: number }[] {
	const out = new Map<string, number>();
	for (const raw of data.getAll('jump')) {
		if (typeof raw !== 'string') continue;
		const [id, version] = raw.split(':');
		const n = Number(version);
		if (isUuid(id) && /^\d{1,9}$/.test(version ?? '') && n >= 1 && !out.has(id.toLowerCase())) {
			out.set(id.toLowerCase(), n);
		}
		if (out.size === IDS_MAX) break;
	}
	return [...out].map(([id, version]) => ({ id, version }));
}

/** The change fields as typed, to show them again after a refusal. */
export function batchEcho(data: FormData): BatchForm {
	return {
		jump_type: field(data, 'jump_type', { max: 16 }),
		at: field(data, 'at', { max: 64 }).toLowerCase(),
		set_aircraft: field(data, 'set_aircraft', { max: 4 }) === '1',
		aircraft: field(data, 'aircraft', { max: 120 }),
		set_gear: field(data, 'set_gear', { max: 4 }) === '1',
		component_ids: uuids(data, 'component_ids', 20)
	};
}

/** What every chosen jump gets, or an error code when nothing (valid) is chosen. */
export function batchChanges(
	data: FormData
): { changes: BatchChanges; form: BatchForm } | { error: string } {
	const jumpType = field(data, 'jump_type', { max: 16 });
	const at = field(data, 'at', { max: 64 }).toLowerCase();
	const setAircraft = field(data, 'set_aircraft', { max: 4 }) === '1';
	const setGear = field(data, 'set_gear', { max: 4 }) === '1';
	if (jumpType && !(jumpType in JUMP_TYPE_LABEL)) return { error: 'invalid_input' };
	const place = at ? AT.exec(at) : null;
	if (at && !place) return { error: 'location_required' };

	const changes: BatchChanges = {};
	if (jumpType) changes.jump_type = jumpType;
	if (place) {
		changes.venue_id = place[1] === 'venue' ? place[2] : null;
		changes.place_id = place[1] === 'place' ? place[2] : null;
	}
	const aircraft = setAircraft ? text(data, 'aircraft', 120) : null;
	if (setAircraft) changes.aircraft = aircraft;
	const components = setGear ? uuids(data, 'component_ids', 20) : [];
	if (setGear) changes.component_ids = components;
	if (Object.keys(changes).length === 0) return { error: 'nothing_to_change' };
	return {
		changes,
		form: {
			jump_type: jumpType,
			at: place ? at : '',
			set_aircraft: setAircraft,
			aircraft: aircraft ?? '',
			set_gear: setGear,
			component_ids: components
		}
	};
}
