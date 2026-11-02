# Implementation assessment

Assessment recorded on 2026-11-02 against commit `1f805de`. This describes an early prototype, not a production-readiness certification. No application fixes were made as part of the product documentation.

## Existing foundation

FastAPI/SQLModel backend, PostgreSQL deployment configuration, React frontend, authentication, account management, aircraft/instructor records, loads, jumps, weather records, and analytics endpoints. The data model has no Dropzone, persistent Jumper profile, Booking, LogbookEntry, Gear, or shared verification entities.

| Area | Repository observation |
| --- | --- |
| Aircraft | Basic records, capacity, active status, and management interface |
| Instructors | Records and tandem/AFF certification flags; creation route has incorrect CRUD keyword |
| Loads | Aircraft, schedule, altitude, statuses, notes, list/edit interface; creation route has incorrect CRUD keyword |
| Jumps | Individual jump records and API routes; scheduling/editing UI is a placeholder |
| Optimization | Frontend sorting/grouping heuristic; apply handler does not save ordering |
| Weather | Stored reports and suitability flags; no live provider found; UI contains hardcoded temperature |
| Analytics | Endpoints reference missing or mismatched functions; frontend analytics file is empty |
| Permissions | Domain routes use authenticated-user access; no dropzone ownership isolation or operational role model |
| Domain testing | No dedicated load/jump/aircraft/instructor/weather/optimization/analytics test files found in the inspected test trees |

## Findings that block a meaningful operational pilot

### Creation endpoints have mismatched arguments

[Load creation](../../backend/app/api/routes/loads.py) calls `crud.create_load(..., load_create=...)`, while [CRUD](../../backend/app/crud.py) expects `load_in`. [Jump creation](../../backend/app/api/routes/jumps.py) similarly supplies `jump_create` instead of `jump_in`. Instructor and weather creation repeat the same pattern.

Earlier isolated API probes returned HTTP 500 for valid load and jump creation requests. The instructor/weather mismatches were observed in code, not exercised in those probes.

### Operational capacity and assignment model is incomplete

`get_available_load_capacity` subtracts the number of jump records from aircraft capacity. A linked instructor does not automatically count as another occupant. The model has one instructor link per jump and no explicit multiple-instructor or camera-flyer assignment model.

An isolated CRUD probe accepted two tandem passengers with the same instructor and duplicate exit-order positions on an aircraft configured with capacity two. This demonstrates missing domain constraints; it is not a simulation of actual aircraft loading.

There is no modeled group identity, load weight/balance calculation, staff turnaround enforcement, or aircraft/resource scheduling conflict protection. Concurrent booking races were not tested.

### Updates bypass key validation

The jump update route directly calls `sqlmodel_update`. An isolated API probe removed the required instructor from an existing tandem jump and received HTTP 200. Transfers, type changes, load status changes, and aircraft capacity changes need consistent validation across all mutation paths.

### Operational permissions are insufficient for a shared service

Domain routes accept `CurrentUser` without a dropzone role or ownership condition. A probe using an overridden ordinary user successfully changed a load status. Authentication was deliberately overridden for isolation, so this was not an end-to-end signup/login exploit test. It demonstrates the route's lack of an operational-role check.

### Some endpoints reference unavailable functions

Examples include `add_jumper_to_load`, `remove_jumper_from_load`, `get_load_capacity_info`, `assign_instructor_to_jump`, `calculate_load_revenue`, and `get_instructor_workload`.

`get_load_statistics` requires a `load_id` that its aggregate route does not provide. Date-filtered jump distribution refers to `Load` without importing it into the relevant scope.

Earlier probes returned HTTP 500 for capacity, load statistics, revenue, instructor workload, instructor assignment, and date-filtered jump distribution. Revenue estimates in CRUD use hardcoded prices; they are not accounting records.

### Visible controls overstate available workflow

[Jump management](../../frontend/src/routes/_layout/jumps.tsx) contains the text “Jump scheduling form will be implemented here” and a submit button without the corresponding scheduling behavior. Completed and pending counters are hardcoded to zero.

[Load optimization apply](../../frontend/src/routes/_layout/loads.tsx) closes the dialog and invalidates the query; it does not persist the proposed order.

### Optimization lacks verified inputs and rules

[The optimizer adapter](../../frontend/src/components/LoadOptimizer/LoadOptimizer.tsx) defaults missing experience, weight, and exit altitude. [The algorithm](../../frontend/src/utils/loadOptimization.ts) applies tandem-first sorting and fixed timing assumptions. It lacks the group, discipline, wind, aircraft, and local-operating context needed to justify general claims of an optimal exit order.

An executed function check selected two tandem passenger records for two slots and produced no instructor warning for their shared instructor. Suggestions must remain experimental and operator-reviewed until the intended operational rules and real input data are validated.

## Validation already performed during discovery

| Check | Result and limitation |
| --- | --- |
| Static inspection | Routes, models, CRUD, relevant frontend pages/components, and test inventory inspected |
| Isolated API probes | FastAPI TestClient, SQLite in-memory database, overridden database/auth dependencies; failures and accepted invalid updates described above |
| CRUD probe | In-memory capacity and duplicate-instructor/exit-order behavior reproduced |
| Optimizer execution | TypeScript transpiled in memory and selected functions executed with sample records |
| TypeScript command | `tsc -p tsconfig.build.json --noEmit` exited successfully; this is not proof of runtime or complete TSX validation |
| Vite bundling | Completed, but route generation first created a placeholder from the empty analytics route; generated repository edits were reverted |

These were ad hoc checks, not a committed regression suite. Temporary build output was removed. The standard pytest suite was not run; its fixtures initialize and delete database records, so it was not appropriate to point it at an unknown existing database during a read-only product review.

PostgreSQL behavior, migration execution, deployed authentication, browser journeys, hardware compatibility, live weather, offline recovery, load concurrency, and real dropzone operations remain untested. This documentation task rechecked key source findings but did not repeat runtime probes.

## Proposed implementation foundations

The following are conceptual responsibilities, not an approved schema or service architecture:

| Responsibility | Candidate concepts |
| --- | --- |
| Identity and access | Person/jumper profile, account, Dropzone, membership, staff role |
| Portable records | LogbookEntry, qualification, verification, sharing grant, correction history |
| Local operations | Load, occupant assignment, group, staff assignment, aircraft, resource availability |
| Commercial booking | Offering, inventory, Booking, cancellation, payment reference where in scope |
| Equipment | Rig, component, service record, rental allocation |
| Telemetry/media | Original upload, parser version, normalized track, derived metrics, attachment |
| Training/events | Goal, session, sign-off, event, registration, participant group |

A completed operational assignment can suggest a personal log entry. Preserve references between them without treating them as the same record. Sharing a personal record must not grant access to the originating dropzone's private operational or commercial data.
