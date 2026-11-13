import type { Page } from '@playwright/test';

/**
 * Unfold the jump form's optional sections (number and altitudes, equipment, notes), as a
 * person would by clicking each summary. Sections already open stay open.
 */
export async function openJumpSections(page: Page): Promise<void> {
	const closed = page.locator('form details.section:not([open]) > summary');
	while ((await closed.count()) > 0) await closed.first().click();
}
