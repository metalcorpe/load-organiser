import { describe, expect, it } from 'vitest';
import { postEventText, postMessage, shareBlock } from './posts.ts';

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

describe('shareBlock', () => {
	const profile = { hidden: false, publishing_restricted: false };

	it('allows sharing with an open switch and a usable profile', () => {
		expect(shareBlock({ publishing_open: true, profile })).toBeNull();
	});

	it('puts the owner pause first, whatever the profile', () => {
		expect(shareBlock({ publishing_open: false, profile })).toBe('publishing_paused');
		expect(shareBlock({ publishing_open: false, profile: null })).toBe('publishing_paused');
		expect(
			shareBlock({ publishing_open: false, profile: { hidden: true, publishing_restricted: true } })
		).toBe('publishing_paused');
	});

	it('then needs a profile that is neither hidden nor restricted', () => {
		expect(shareBlock({ publishing_open: true, profile: null })).toBe('profile_required');
		expect(shareBlock({ publishing_open: true, profile: { ...profile, hidden: true } })).toBe('profile_hidden');
		expect(
			shareBlock({ publishing_open: true, profile: { ...profile, publishing_restricted: true } })
		).toBe('publishing_restricted');
	});

	it('has a message for every reason', () => {
		for (const code of ['publishing_paused', 'profile_required', 'profile_hidden', 'publishing_restricted']) {
			expect(postMessage(code)).not.toBe(postMessage('invalid_input'));
		}
	});
});
