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
6. **Migration round trip on the restored data:** downgrade every beta migration
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

## Known gap: deletions and revocations after the backup

A backup is the database at one moment. Restoring a backup taken at time T brings
back everything deleted after T, including:

- jumps, gear, plans and posts a person deleted or unpublished
- follows removed or blocks added
- profiles a reviewer hid
- sessions that were revoked, for example after a password change or "sign out
  everywhere"

The architecture requires replaying deletions and revocations before accepting data
again. **That replay is not built.** Until it is, a restore must be followed by:

1. **Revoke all sessions.** Delete every row of `skydiver_session`, so everyone signs
   in again and no revoked session is valid.
2. **Close intake.** Keep registration closed (`SKYDIVER_REGISTRATION_OPEN=false`) and
   keep the web app away from the restored API until step 3 is done. No switch that
   stops writes for existing accounts exists yet.
3. **Re-apply known changes.** Re-apply every unpublish, deletion, block and
   moderation decision recorded after T from the application logs and reviewer
   records. This depends on those being kept: no such journal exists yet.

Production data intake should not be approved until this is either built or
accepted in writing as a manual procedure with a known gap (#161 acceptance).

## Production procedure (to repeat with the selected hosts)

1. **Backup source** (**needs accounts**):
   - Use Neon's own history and branching for point-in-time recovery inside its
     retention window. Record the window the account actually provides.
   - Take a separate `pg_dump -Fc` with the PostgreSQL 18 client over the **direct**
     (non-pooled) connection string, to an encrypted destination outside Neon. That
     destination is not chosen; free durable storage is an open gate.
2. **Restore test:** restore the latest dump into a new Neon branch or a local
   database. Run `recovery.py snapshot` on both and compare, then run the smoke check
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
