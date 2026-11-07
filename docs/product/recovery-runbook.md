# Recovery runbook and local drill (#161)

Status 2026-11-07: **local drill only.** No hosting account, deployment, backup
destination or production data exists. This document records what the local drill
proves and the procedure to repeat it against the selected hosts once the owner has
created accounts. Account-dependent steps are marked **needs accounts**.

## Local drill: what it proves

`scripts/verify.sh recovery` (part of the default `verify.sh` run) uses disposable
databases on a throwaway PostgreSQL 17 cluster:

1. **Seed through the real API** (`app/tests/skydiver/recovery.py seed`):
   - accounts and profiles, an approved follow, a listed dropzone
   - a component with a service entry, a private place
   - a jump that uses the component, and a second jump that is then deleted
   - a prior-history baseline and a visit plan
   - a follower-only post that shares the dropzone, and a profile report
   - a session that is then revoked
2. **Back up** with `pg_dump -Fc`.
3. **Restore** with `pg_restore --exit-on-error --no-owner` into an empty database.
4. **Compare data and schema:**
   - Row count and full-content digest of every table must match before and after.
   - The seeded tables must be non-empty, so the comparison cannot pass on an
     empty database.
   - The restored schema must match the source schema (`pg_dump --schema-only`).
     Finding: restore re-parses CHECK constraints, and PostgreSQL deparses varchar
     `IN` lists as an equivalent but differently cast `ARRAY`. Those lines are
     compared without casts and parentheses; every other line must match exactly.
5. **Behaviour after restore** (`recovery.py check`):
   - the kept jump's private note is intact and the deleted jump stays deleted
   - the revoked session stays revoked and the baseline is intact
   - the follower can read the post; a stranger and a guest cannot
   - the dropzone activity lists the post for the follower
   - the restored database accepts a compare-and-swap write
6. **Ledger replay:** changes made on the source after the backup reach the restored
   copy through the exported erasure ledger (see below).
7. **Migration round trip on the restored data:** downgrade every beta migration
   (to `c6459ca8ce2a`, the last legacy revision) and upgrade to head again. The
   resulting schema must equal a fresh migration's schema (`pg_dump --schema-only`,
   ignoring the per-dump `\restrict` key).

Result on 2026-11-07: passed.

### Limits of the local drill

- **Engine:** PostgreSQL 17 locally; Neon runs PostgreSQL 18. `pg_dump` must be at
  least the server's major version, so production dumps need the 18 client.
- **Legacy downgrades:** the template migrations below `c6459ca8ce2a` cannot be
  downgraded (an unnamed foreign key in "Add cascade delete relationships"). Legacy
  code is outside the beta (#166).
- **Data loss on downgrade:** downgrades drop the data of the tables they remove (for
  example post reports in `b7d1f4a2c9e5`). A downgrade is a schema rollback, not a
  data-preserving operation; restore from backup to recover data.
- **Not exercised:** backup encryption, a durable off-site destination, scheduling,
  key custody, restore time on realistic data volume, and connection limits.

## Deletions and revocations after the backup: the erasure ledger

A backup is the database at one moment. Restoring a backup taken at time T brings
back everything deleted or revoked after T. Architecture A9 requires replaying those
changes before the restored database serves anyone. Built 2026-11-07, local only:

- **Recording.** Database triggers (migration `d4f9b6a2e8c1`) add an entry to
  `skydiver_erasure_ledger` in the same transaction as each of these changes, so no
  application path can skip it:
  - deleted rows: accounts, jumps, posts, follows, blocks (unblock), components,
    service entries, private places, plans, saved listings, the history baseline
    and reviewer role grants, including rows removed by a cascade
  - new blocks
  - changes to account `is_active`, profile `discoverable`, `hidden_at` and
    `publishing_restricted_at`, and post `audience`
  - a new password (from change or reset; not a rehash at sign-in), recorded by the
    identity store
  Entries hold row keys and the changed values only (ids, flags, times), never notes,
  captions, names or other free text.
- **Export** (`python -m app.skydiver.recovery.ledger export FILE`): writes every entry
  as JSON lines, replacing the file atomically. Copies must live outside the backup
  set (**needs accounts**: same open gate as the backup destination) and be taken
  more often than backups. Changes made after the last export are lost if the
  database itself is lost; no schedule or interval is chosen yet.
- **Prune** (`... ledger prune DAYS`): drops entries older than DAYS. Keep entries
  longer than the oldest backup that could be restored (seven daily copies: at least
  8 days). Until pruned, the ledger keeps the ids of deleted rows.
- **Replay** (`... ledger apply FILE [FILE ...]`), on the restored database, before
  it serves traffic, in one transaction:
  1. merges the entries of the files with those in the restored ledger (an entry
     that differs between copies stops the replay) and adds the missing ones back
  2. applies them in recording order, with recording switched off: deletes by key,
     re-inserts blocks, sets recorded values; a component's jump links are removed
     before the component, since deletion proves no jump used it any more
  3. replaces each password changed after T with an unknown one: the new password is
     not in the restored copy, so that person resets it by email
  4. revokes every session and deletes every email or reset token
  It prints counts per action and table. An entry that cannot be applied is rolled
  back alone and listed under `skipped`, for example a private place still used by a
  restored jump (a jump needs its place, and its later location is not recorded).
  A second replay changes nothing except the unknown passwords.

**Drill evidence** (`scripts/verify.sh recovery`, 2026-11-07, passed): after the
backup the drill unpublishes a post, removes a follower, blocks a person, stops using
and deletes a component, deletes a place and a plan, turns off discoverability,
changes a password and deletes a second account. It exports the ledger from the
source, replays it on the restored copy, and checks that none of these came back,
that every older session and the old password are refused, that the kept jump is
intact, and that a second replay leaves every table except `user` unchanged.

**Still lost or reverted by a restore** (not erasures, so not recorded): edits after
T to notes, captions, names, bios and other fields revert to their state at T;
records created after T, including reports, suggestions and reviewer decisions, are
missing; email address changes are not recorded. Restoring still needs registration
closed (`SKYDIVER_REGISTRATION_OPEN=false`) and the web app kept away from the API
until the replay has run. No switch stops writes for existing accounts.

Not verified: the replay against Neon, against a production-sized ledger, or with a
real email sender for the password resets it forces. Production data intake still
waits on a ledger export destination and schedule (#161 acceptance).

## Production procedure (to repeat with the selected hosts)

1. **Backup source** (**needs accounts**):
   - Use Neon's own history and branching for point-in-time recovery inside its
     retention window. Record the window the account actually provides.
   - Take a separate `pg_dump -Fc` with the PostgreSQL 18 client over the **direct**
     (non-pooled) connection string, to an encrypted destination outside Neon. That
     destination is not chosen; free durable storage is an open gate.
2. **Restore test:** restore the latest dump into a new Neon branch or a local
   database, then replay the exported ledger (`ledger apply`). Run `recovery.py snapshot` on both and compare, then run the smoke check
   against the restored copy with test accounts only.
3. **Migrations** (**needs accounts**):
   - Run `alembic upgrade head` over the direct connection before deploying the API
     version that needs it.
   - The API uses the pooled connection.
   - Take a dump immediately before every migration.
4. **Rollback:**
   - Prefer restoring the pre-migration dump or Neon branch.
   - Use `alembic downgrade` only when the dropped data is acceptable to lose (see
     "Data loss on downgrade").
5. **Record** each drill: date, dump size, restore duration, the snapshot comparison
   result and who performed it. The recovery owner is not yet named.
