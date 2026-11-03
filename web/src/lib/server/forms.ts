/** Reads a bounded string field from a form submission. Never trims passwords. */
export function field(
	data: FormData,
	name: string,
	{ max = 1024, trim = false }: { max?: number; trim?: boolean } = {}
): string {
	const raw = data.get(name);
	if (typeof raw !== 'string') return '';
	const value = trim ? raw.trim() : raw;
	return value.slice(0, max);
}
