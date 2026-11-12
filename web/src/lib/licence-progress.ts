/** Progress toward the next USPA licence (USPA SIM 3-1), as shown to the jumper. Client-safe. */
import { LICENCE_LABEL, isLicence } from './currency.ts';

/** The fields of LicenceProgressOut the wording needs. */
export interface ProgressIn {
	licence: string;
	next_licence: string | null;
	jumps: number;
	jumps_required: number | null;
	jumps_include_prior: boolean;
	freefall_seconds: number;
	freefall_required_seconds: number | null;
	entries_without_freefall: number;
}

export const OTHER_REQUIREMENTS =
	'Other requirements (skills, proficiency card, landing accuracy, endorsements) are checked by USPA and your instructors, not by this app (USPA SIM 3-1).';

const n = (value: number) => value.toLocaleString('en-GB');
const plural = (count: number, one: string, many: string) => `${n(count)} ${count === 1 ? one : many}`;

/** Freefall time in plain words: minutes below two hours, then hours and minutes. */
export function duration(seconds: number): string {
	const minutes = Math.floor(seconds / 60);
	if (minutes < 120) return plural(minutes, 'minute', 'minutes');
	const hours = Math.floor(minutes / 60);
	const rest = minutes % 60;
	return rest ? `${plural(hours, 'hour', 'hours')} ${plural(rest, 'minute', 'minutes')}` : plural(hours, 'hour', 'hours');
}

function label(licence: string | null): string {
	return licence && isLicence(licence) ? LICENCE_LABEL[licence] : '';
}

/** "Toward a C licence", "Toward an A licence"; null for D (there is no next licence). */
export function towardText(p: Pick<ProgressIn, 'next_licence'>): string | null {
	if (!p.next_licence) return null;
	return `Toward ${p.next_licence === 'a' ? 'an' : 'a'} ${label(p.next_licence)}`;
}

export interface ProgressLines {
	toward: string | null;
	jumps: string | null;
	freefall: string | null;
	missing: string | null;
	prior: string | null;
	highest: string | null;
}

export function progressLines(p: ProgressIn): ProgressLines {
	const toward = towardText(p);
	if (!toward || p.jumps_required === null) {
		return {
			toward: null,
			jumps: null,
			freefall: null,
			missing: null,
			prior: null,
			highest: `You stated a ${label(p.licence)}, the highest USPA licence: there is no next licence to track.`
		};
	}
	const left = p.jumps_required - p.jumps;
	const jumps = `Jumps: ${n(p.jumps)} of ${n(p.jumps_required)} (${left > 0 ? `${n(left)} to go` : 'reached'}).`;
	let freefall: string | null = null;
	let missing: string | null = null;
	if (p.freefall_required_seconds) {
		const need = p.freefall_required_seconds - p.freefall_seconds;
		freefall = `Recorded freefall time: ${duration(p.freefall_seconds)} of ${duration(p.freefall_required_seconds)} (${need > 0 ? `${duration(need)} to go` : 'reached'}).`;
		if (p.entries_without_freefall > 0) {
			missing = `${plural(p.entries_without_freefall, 'entry has', 'entries have')} no freefall time, so ${p.entries_without_freefall === 1 ? 'it adds' : 'they add'} none.`;
		}
	}
	const prior = p.jumps_include_prior
		? 'Your declared prior jump count is in the jump total but not in the freefall time: it has none recorded.'
		: null;
	return { toward, jumps, freefall, missing, prior, highest: null };
}

/** One line for the Logbook, beside the currency status; null when there is no next licence. */
export function progressSummary(p: ProgressIn): string | null {
	const toward = towardText(p);
	if (!toward || p.jumps_required === null) return null;
	const parts = [`${n(p.jumps)} of ${n(p.jumps_required)} jumps`];
	if (p.freefall_required_seconds) {
		parts.push(
			`${duration(p.freefall_seconds)} of ${duration(p.freefall_required_seconds)} of freefall`
		);
	}
	return `${toward}: ${parts.join(', ')}.`;
}
