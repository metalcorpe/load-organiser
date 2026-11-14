import { expect, type Page } from '@playwright/test';

/**
 * Unfold the jump form's optional sections (number and altitudes, equipment, notes), as a
 * person would by clicking each summary. Sections already open stay open. It waits for the
 * page to hydrate first: hydration sets each section's initial open state again, so a
 * section unfolded before it would fold back.
 */
export async function openJumpSections(page: Page): Promise<void> {
	await expect(page.locator('html[data-form-guard="ready"]')).toHaveCount(1);
	const closed = page.locator('form details.section:not([open]) > summary');
	while ((await closed.count()) > 0) await closed.first().click();
}
