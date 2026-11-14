/**
 * A dropzone's details as its source states them (owner decision 2026-11-14): who runs
 * it, its season and aircraft. They name the operator; they are not a claim,
 * endorsement or verification. Client-safe.
 */

/** Operator rows in the reviewer form; the service keeps at most 4. */
export const OPERATOR_ROWS = 4;

export type VenueOperator = { name: string; url: string | null };
