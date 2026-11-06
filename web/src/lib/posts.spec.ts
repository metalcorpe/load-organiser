import { describe, expect, it } from 'vitest';
import { postEventText, postMessage } from './posts.ts';

describe('post history lines', () => {
	it('explains why a post left, without inventing detail', () => {
		expect(postEventText('post_published', { audience: 'followers' })).toBe(
			'Published to approved followers'
		);
		expect(postEventText('post_withdrawn', { reason: 'shared_field_changed' })).toBe(
			'Post withdrawn: you changed a value it shared'
		);
		expect(postEventText('post_withdrawn', { reason: 'profile_not_discoverable' })).toContain(
			'stopped being discoverable'
		);
		expect(postEventText('post_removed', { reason: 'Advertising.' })).toBe(
			'Post removed by a reviewer: Advertising.'
		);
		expect(postEventText('corrected', {})).toBeNull();
	});

	it('maps unknown codes to a generic message', () => {
		expect(postMessage('public_needs_discoverable')).toContain('discoverable profile');
		expect(postMessage('something_new')).toBe('Check the details you entered.');
		expect(postMessage(undefined)).toBeUndefined();
	});
});
