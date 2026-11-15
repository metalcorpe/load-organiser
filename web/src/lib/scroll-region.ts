import type { Attachment } from 'svelte/attachments';

let captions = 0;

/**
 * For a .table-scroll box around a data table. With large text on a small screen the table can
 * be wider than the page; it then scrolls sideways inside this box (WCAG 1.4.10 allows this for
 * data tables) instead of widening the page. Only while it scrolls is the box a region named by
 * the table's caption, with a tab stop, so a keyboard can scroll it too (Safari does not focus a
 * scrolling box on its own). At ordinary sizes it adds no tab stop and no landmark.
 */
export const scrollRegion: Attachment<HTMLElement> = (box) => {
	const caption = box.querySelector('caption');
	if (caption && !caption.id) caption.id = `scroll-caption-${++captions}`;

	const update = () => {
		if (box.scrollWidth > box.clientWidth + 1) {
			box.tabIndex = 0;
			box.setAttribute('role', 'region');
			if (caption) box.setAttribute('aria-labelledby', caption.id);
		} else {
			box.removeAttribute('tabindex');
			box.removeAttribute('role');
			box.removeAttribute('aria-labelledby');
		}
	};
	// The box keeps the page's width while the table inside it grows, so both are watched.
	const observer = new ResizeObserver(update);
	observer.observe(box);
	if (box.firstElementChild) observer.observe(box.firstElementChild);
	return () => observer.disconnect();
};
