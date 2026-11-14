import { describe, expect, it } from 'vitest';
import {
	errorSummary,
	fieldErrorsForReason,
	fieldMessage,
	firstInvalid,
	registrationErrors,
	signInErrors
} from './account-form.ts';
import { fieldsFor } from './field-errors.ts';

describe('sign-in field checks', () => {
	it('names each missing field', () => {
		const errors = signInErrors({ email: '', password: '' });
		expect(errors).toEqual({ email: 'email_required', password: 'password_required' });
		expect(firstInvalid(errors)).toBe('email');
		expect(errorSummary(errors)).toBe('Enter your email address. Enter your password.');
	});

	it('catches an address without an @, and passes a plausible one', () => {
		expect(signInErrors({ email: 'jumper', password: 'x' })).toEqual({ email: 'email_invalid' });
		expect(signInErrors({ email: 'a b@example.com', password: 'x' })).toEqual({
			email: 'email_invalid'
		});
		expect(signInErrors({ email: 'jumper@example.com', password: 'x' })).toEqual({});
	});

	it('never judges the password beyond its presence', () => {
		expect(signInErrors({ email: 'a@b', password: ' ' })).toEqual({});
	});
});

describe('registration field checks', () => {
	it('names the required fields and leaves the optional name alone', () => {
		const errors = registrationErrors({ email: '', password: '', confirm: '' });
		expect(errors).toEqual({ email: 'email_required', password: 'new_password_required' });
		expect(errorSummary(errors)).toBe(
			'Enter your email address. Choose a password of 15 to 128 characters.'
		);
	});

	it('asks for the repeat, and then for a matching one', () => {
		const ok = { email: 'a@example.com', password: 'correct horse battery staple' };
		expect(registrationErrors({ ...ok, confirm: '' })).toEqual({
			password_confirm: 'password_confirm_required'
		});
		expect(registrationErrors({ ...ok, confirm: 'something else' })).toEqual({
			password_confirm: 'password_mismatch'
		});
		expect(registrationErrors({ ...ok, confirm: ok.password })).toEqual({});
	});

	it('leaves password length to the API, then places its refusal on the field', () => {
		expect(registrationErrors({ email: 'a@b', password: 'short', confirm: 'short' })).toEqual({});
		expect(fieldErrorsForReason('password_too_short')).toEqual({ password: 'password_too_short' });
		expect(fieldErrorsForReason('invalid_credentials')).toEqual({});
		expect(fieldMessage('password_too_short')).toBe('Use at least 15 characters.');
	});

	it('focuses the first problem in form order', () => {
		expect(
			firstInvalid({ password_confirm: 'password_mismatch', email: 'email_invalid' })
		).toBe('email');
	});
});

describe('focus after a refused post', () => {
	it.each([
		['email_required', 'email'],
		['email_invalid', 'email'],
		['password_required', 'password'],
		['new_password_required', 'password'],
		['password_confirm_required', 'password_confirm'],
		['password_mismatch', 'password_confirm']
	])('%s points FormGuard at %s', (code, name) => {
		expect(fieldsFor(code)).toContain(name);
	});
});
