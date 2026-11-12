import { describe, expect, it } from 'vitest';
import { appliedText, batchHeading, batchMessage, changeText, undoneText } from './jump-batch.ts';

describe('changeText', () => {
	it('names each value every jump gets, in a fixed order', () => {
		expect(
			changeText({
				gear: ['Sabre 170'],
				aircraft: 'Cessna 208',
				place: 'Farm strip (private place)',
				jumpType: 'freefly'
			})
		).toBe('type → Freefly; place → Farm strip (private place); aircraft → Cessna 208; gear used → Sabre 170');
	});

	it('says plainly when a value is cleared, and leaves out what is kept', () => {
		expect(changeText({ aircraft: null, gear: [] })).toBe('aircraft → none; gear used → none');
		expect(changeText({})).toBe('');
	});
});

describe('batchHeading', () => {
	it('counts the jumps', () => {
		expect(batchHeading(23, { jumpType: 'freefly', aircraft: 'Cessna 208' })).toBe(
			'Change 23 jumps: type → Freefly; aircraft → Cessna 208'
		);
		expect(batchHeading(1, { jumpType: 'angle' })).toBe('Change 1 jump: type → Angle / tracking');
	});
});

describe('outcomes', () => {
	it('reports skipped jumps as left alone', () => {
		expect(appliedText(3, 0, 0)).toBe('Changed 3 jumps.');
		expect(appliedText(2, 1, 1)).toBe(
			'Changed 2 jumps. 1 jump was left as it was: edited or deleted since you checked. 1 jump already had these values.'
		);
		expect(undoneText(2, 2)).toBe(
			'Put back 2 jumps. 2 jumps were left as they are: edited since the change, or an earlier place or gear is no longer available.'
		);
	});

	it('explains refusals, with a fallback', () => {
		expect(batchMessage('too_many_jumps')).toBe('Choose at most 200 jumps at a time.');
		expect(batchMessage('something_new')).toBe('Check what you chose.');
		expect(batchMessage(undefined)).toBeUndefined();
	});
});
