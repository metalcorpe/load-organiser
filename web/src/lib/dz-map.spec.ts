import { describe, expect, it } from 'vitest';
import { dzHref, dzView, formatCoordinates, mapChosen, osmLink, rememberMapChoice } from './dz-map.ts';

function memoryStorage(): Storage {
	const values = new Map<string, string>();
	return {
		get length() {
			return values.size;
		},
		clear: () => values.clear(),
		getItem: (key) => values.get(key) ?? null,
		key: (index) => [...values.keys()][index] ?? null,
		removeItem: (key) => void values.delete(key),
		setItem: (key, value) => void values.set(key, value)
	};
}

describe('dropzone map helpers', () => {
	it('reads the view, defaulting to the list', () => {
		expect(dzView('map')).toBe('map');
		expect(dzView(null)).toBe('list');
		expect(dzView('MAP')).toBe('list');
		expect(dzView('satellite')).toBe('list');
	});

	it('builds shareable directory links that keep the filters', () => {
		expect(dzHref({})).toBe('/dz');
		expect(dzHref({ view: 'list', q: 'empuria' })).toBe('/dz?q=empuria');
		expect(dzHref({ q: 'a b&c', country: 'ES', view: 'map' })).toBe(
			'/dz?q=a+b%26c&country=ES&view=map'
		);
		expect(dzHref({ country: 'PT', cursor: 'abc' })).toBe('/dz?country=PT&cursor=abc');
	});

	it('links to the point on openstreetmap.org', () => {
		expect(osmLink(42.25857, -3.137)).toBe(
			'https://www.openstreetmap.org/?mlat=42.25857&mlon=-3.137#map=13/42.25857/-3.137'
		);
	});

	it('writes coordinates with hemispheres', () => {
		expect(formatCoordinates(42.25857, 3.137)).toBe('42.25857° N, 3.13700° E');
		expect(formatCoordinates(-33.9, -70.1234567)).toBe('33.90000° S, 70.12346° W');
	});

	it('remembers the choice to show the map, and survives storage that fails', () => {
		const storage = memoryStorage();
		expect(mapChosen(() => storage)).toBe(false);
		rememberMapChoice(() => storage);
		expect(mapChosen(() => storage)).toBe(true);

		const broken = () => {
			throw new DOMException('denied', 'SecurityError');
		};
		expect(mapChosen(broken)).toBe(false);
		expect(() => rememberMapChoice(broken)).not.toThrow();
		expect(mapChosen(() => undefined)).toBe(false);
	});
});
