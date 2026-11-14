/**
 * The dropzone map, drawn with Leaflet and Leaflet.markercluster over OpenStreetMap tiles.
 *
 * Browser only, and imported dynamically by DropzoneMap.svelte once the visitor chooses to
 * show the map: neither library nor its CSS is in the page bundle, and no tile is requested
 * before that choice. Popup content is built with DOM text nodes, never HTML strings.
 */
import L from 'leaflet';
// Registers L.markerClusterGroup on the Leaflet object above (its UMD build reads window.L,
// which Leaflet sets when it loads; module order keeps Leaflet first).
import 'leaflet.markercluster';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import { TILE_ATTRIBUTION, TILE_REFERRER_POLICY, TILE_URL } from './dz-map.ts';

export interface MapPoint {
	id: string;
	name: string;
	/** "Locality, Country", already formatted for reading. */
	place: string;
	lat: number;
	lon: number;
	closed: boolean;
}

export interface DropzoneMapHandle {
	destroy(): void;
}

/** Europe, when there is nothing to fit the view to. */
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

export function createDropzoneMap(
	container: HTMLElement,
	points: MapPoint[],
	options: { reducedMotion: boolean }
): DropzoneMapHandle {
	const animate = !options.reducedMotion;
	const map = L.map(container, {
		zoomAnimation: animate,
		fadeAnimation: animate,
		markerZoomAnimation: animate,
		worldCopyJump: true
	});
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
		marker.bindPopup(() => popupContent(point), { minWidth: 160, maxWidth: 260 });
		// Opened from the keyboard, the popup takes focus so its link can be reached; on close,
		// focus goes back to the marker instead of being lost.
		let fromKeyboard = false;
		marker.on('popupopen', (event: L.PopupEvent) => {
			fromKeyboard = document.activeElement === marker.getElement();
			const link = event.popup.getElement()?.querySelector<HTMLAnchorElement>('.dz-popup-name a');
			if (fromKeyboard && link) link.focus();
		});
		marker.on('popupclose', (event: L.PopupEvent) => {
			const active = document.activeElement;
			const lost = !active || active === document.body;
			if (fromKeyboard && (lost || event.popup.getElement()?.contains(active))) {
				marker.getElement()?.focus();
			}
			fromKeyboard = false;
		});
		group.addLayer(marker);
	}
	map.addLayer(group);

	if (points.length > 0) {
		map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lon] as L.LatLngTuple)), {
			padding: [24, 24],
			maxZoom: 10,
			animate: false
		});
	} else {
		map.setView(FALLBACK, 4);
	}

	return {
		destroy() {
			map.remove();
		}
	};
}
