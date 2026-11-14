/**
 * The dropzone map, drawn with Leaflet and Leaflet.markercluster over OpenStreetMap tiles.
 *
 * Browser only, and imported dynamically by DropzoneMap.svelte once the visitor chooses to
 * show the map: the libraries' JavaScript and CSS (imported below) are not in the page bundle
 * and load with this chunk, and no tile is requested before that choice. Popup content is
 * built with DOM text nodes, never HTML strings.
 */
import L from 'leaflet';
// Registers L.markerClusterGroup on the Leaflet object above (its UMD build reads window.L,
// which Leaflet sets when it loads; module order keeps Leaflet first).
import 'leaflet.markercluster';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import {
	ATTRIBUTION_PREFIX,
	TILE_ATTRIBUTION,
	TILE_REFERRER_POLICY,
	TILE_URL,
	startBounds,
	type MapPoint
} from './dz-map.ts';

export type { MapPoint } from './dz-map.ts';

export interface DropzoneMapHandle {
	destroy(): void;
}

/** Mainland Europe, when there is nothing to fit the view to. */
const FALLBACK: L.LatLngTuple = [50, 10];

function text(tag: string, className: string, value: string): HTMLElement {
	const element = document.createElement(tag);
	element.className = className;
	element.textContent = value;
	return element;
}

function markerIcon(point: MapPoint): L.DivIcon {
	// The marker is a focusable role=button (Leaflet's keyboard option); its name is this text.
	const label = text('span', 'visually-hidden', point.closed ? `${point.name} (closed)` : point.name);
	return L.divIcon({
		className: point.closed ? 'dz-marker dz-marker-closed' : 'dz-marker',
		html: label,
		iconSize: [18, 18],
		iconAnchor: [9, 9],
		popupAnchor: [0, -8]
	});
}

function popupContent(point: MapPoint): HTMLElement {
	const box = document.createElement('div');
	box.className = 'dz-popup';
	const title = document.createElement('p');
	title.className = 'dz-popup-name';
	const link = document.createElement('a');
	link.href = `/dz/${encodeURIComponent(point.id)}`;
	link.textContent = point.name;
	title.appendChild(link);
	box.appendChild(title);
	box.appendChild(text('p', 'dz-popup-place', point.place));
	if (point.closed) box.appendChild(text('p', 'dz-popup-closed', 'Closed'));
	return box;
}

function clusterIcon(cluster: L.MarkerCluster): L.DivIcon {
	const count = cluster.getChildCount();
	const box = document.createElement('span');
	box.appendChild(text('span', 'dz-cluster-count', String(count)));
	box.appendChild(text('span', 'visually-hidden', ' dropzones here: zoom in'));
	const size = count < 10 ? 34 : count < 100 ? 40 : 46;
	return L.divIcon({ className: 'dz-cluster', html: box, iconSize: [size, size] });
}

/**
 * Popups from the keyboard: Enter on a marker opens its popup and moves focus to its link;
 * Escape in the popup closes it and returns focus to the marker. A mouse or touch opening
 * leaves focus where it was.
 */
function keyboardPopup(marker: L.Marker): void {
	let enterPressed = false;
	let returnFocus = false;
	marker.on('add', () => {
		marker.getElement()?.addEventListener('keydown', (event) => {
			if (event.key === 'Enter') enterPressed = true;
		});
	});
	marker.on('popupopen', (event: L.PopupEvent) => {
		returnFocus = enterPressed;
		enterPressed = false;
		const element = event.popup.getElement();
		if (!element) return;
		// One handler per popup element (assigned, so reopening does not add another).
		element.onkeydown = (key) => {
			if (key.key !== 'Escape') return;
			key.preventDefault();
			key.stopPropagation();
			returnFocus = true;
			marker.closePopup();
		};
		if (returnFocus) element.querySelector<HTMLAnchorElement>('.dz-popup-name a')?.focus();
	});
	marker.on('popupclose', () => {
		if (returnFocus) marker.getElement()?.focus();
		returnFocus = false;
	});
}

export function createDropzoneMap(
	container: HTMLElement,
	points: MapPoint[],
	options: { reducedMotion: boolean; filtered: boolean }
): DropzoneMapHandle {
	const animate = !options.reducedMotion;
	const map = L.map(container, {
		zoomAnimation: animate,
		fadeAnimation: animate,
		markerZoomAnimation: animate,
		inertia: animate,
		worldCopyJump: true
	});
	if (!animate) {
		// Leaflet has no map-wide switch for animated panning (arrow keys, popup auto-pan,
		// cluster zoom-to-bounds all go through panBy), so this map always pans without it.
		const panBy = map.panBy.bind(map);
		map.panBy = (offset, panOptions) => panBy(offset, { ...panOptions, animate: false });
	}
	// The plain "Leaflet" credit, without the default prefix's flag icon.
	map.attributionControl.setPrefix(ATTRIBUTION_PREFIX);
	L.tileLayer(TILE_URL, {
		maxZoom: 19,
		attribution: TILE_ATTRIBUTION,
		// The site's Referrer-Policy (same-origin) sends no Referer to other hosts, and the
		// OpenStreetMap tile servers refuse requests without one (tile usage policy). Tiles
		// alone send the site's origin, never the page path or query.
		referrerPolicy: TILE_REFERRER_POLICY
	}).addTo(map);

	const group = L.markerClusterGroup({
		showCoverageOnHover: false,
		maxClusterRadius: 50,
		chunkedLoading: true,
		animate,
		iconCreateFunction: clusterIcon
	});
	for (const point of points) {
		const marker = L.marker([point.lat, point.lon], {
			icon: markerIcon(point),
			keyboard: true,
			riseOnHover: true
		});
		marker.bindPopup(() => popupContent(point), {
			minWidth: 160,
			maxWidth: 260,
			autoPanPadding: [16, 16]
		});
		keyboardPopup(marker);
		group.addLayer(marker);
	}
	map.addLayer(group);

	const bounds = startBounds(points, { filtered: options.filtered });
	if (bounds) {
		map.fitBounds(bounds, { padding: [24, 24], maxZoom: 10, animate: false });
	} else {
		map.setView(FALLBACK, 4);
	}

	return {
		destroy() {
			map.remove();
		}
	};
}
