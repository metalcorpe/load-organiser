/** Statistics (/stats): rows for the bar tables and the year filter. Client-safe, no I/O. */
import type { StatsOut } from './contracts/index.ts';
import { count, formatMonth } from './history.ts';
import { JUMP_TYPE_LABEL } from './jumps.ts';
import { formatFreefall } from './print.ts';
import type { BarRow } from './components/BarTable.svelte';

const YEAR = /^\d{4}$/;

/** A four-digit `year` query value, else '' (all years). The API checks the range. */
export function yearParam(raw: string | null): string {
	const value = (raw ?? '').trim();
	return YEAR.test(value) ? value : '';
}

const n = (value: number) => value.toLocaleString('en-GB');

/** Newest first, like History's month table. */
export function yearRows(s: Pick<StatsOut, 'per_year'>): BarRow[] {
	return [...s.per_year].reverse().map((y) => ({ label: String(y.year), value: y.jumps }));
}

export function monthRows(s: Pick<StatsOut, 'per_month'>): BarRow[] {
	return [...s.per_month].reverse().map((m) => ({ label: formatMonth(m.month), value: m.jumps }));
}

export function typeRows(s: Pick<StatsOut, 'by_type'>): BarRow[] {
	return s.by_type.map((t) => ({ label: JUMP_TYPE_LABEL[t.jump_type] ?? t.jump_type, value: t.jumps }));
}

/** The top places by name, then the rest as one "Other places" row. */
export function placeRows(s: Pick<StatsOut, 'by_place'>): BarRow[] {
	const rows: BarRow[] = s.by_place.items.map((p) => ({
		label:
			(p.location.name ?? (p.location.kind === 'venue' ? 'Dropzone no longer listed' : 'Private place')) +
			(p.location.kind === 'place' ? ' (private place)' : ''),
		value: p.jumps
	}));
	if (s.by_place.other_places > 0) {
		rows.push({
			label: `Other places (${n(s.by_place.other_places)})`,
			value: s.by_place.others
		});
	}
	return rows;
}

export function aircraftRows(s: Pick<StatsOut, 'by_aircraft'>): BarRow[] {
	const rows: BarRow[] = s.by_aircraft.items.map((a) => ({ label: a.aircraft, value: a.jumps }));
	if (s.by_aircraft.other_aircraft > 0) {
		rows.push({
			label: `Other aircraft (${n(s.by_aircraft.other_aircraft)})`,
			value: s.by_aircraft.others
		});
	}
	return rows;
}

/** Recorded freefall time per year, newest first, with the jumps that lack one. */
export function freefallRows(s: Pick<StatsOut, 'freefall'>): BarRow[] {
	return [...s.freefall].reverse().map((f) => ({
		label: String(f.year),
		value: f.seconds,
		text: formatFreefall(f.seconds),
		extra: n(f.without_freefall)
	}));
}

/** The total line: recorded jumps, and the reported total with the prior count when it holds. */
export function totalText(s: Pick<StatsOut, 'total' | 'year'>): string {
	const recorded = `${count(s.total.recorded)} recorded${s.year ? ` in ${s.year}` : ' here'}.`;
	if (s.total.reported === null || s.total.prior_jumps === null) return recorded;
	return `${recorded} Reported total ${n(s.total.reported)}, including your declared prior jump count of ${n(s.total.prior_jumps)}.`;
}
