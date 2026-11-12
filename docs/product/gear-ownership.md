# Gear serial numbers and ownership history

Status: proposed extension of F04, prompted by the product owner's question about serial numbers and ownership records. The private inventory part selected for the beta is implemented by #152 (see [Implemented in #152](#implemented-in-152)); transfers, evidence uploads, cross-account matching and disputes are not. It can provide individual value without dropzone adoption.

## User need

A skydiver wants to identify their equipment, retain acquisition and service documents, and record transfers when buying or selling components. A future buyer may want the seller to share the recorded history. These needs and willingness to use the workflow remain unvalidated.

## Component identity

A rig is a changing assembly of separately identifiable equipment. Record container/harness, main canopy, reserve canopy, and AAD independently; other serialized equipment can follow. A component keeps its identity when moved to another rig or transferred independently.

| Field | Proposed behavior |
| --- | --- |
| Component type, manufacturer, model | Describe the physical item; retain original entered values |
| Serial number | Preserve leading zeros, letters, punctuation, and label text; require confirmation of any photo-extracted value |
| Manufacture date | Optional with precision/source recorded; do not invent a day for a month-only label |
| Label and equipment photographs | Private supporting evidence |
| Acquisition date and method | Purchase, gift, inheritance, or another declared acquisition; unknown permitted |
| Receipt or transfer document | Optional private evidence, separate from public item details |
| Rig association | Dated assembly membership; does not change component ownership |

Use an internal item ID. Treat manufacturer/component type/serial information as a matching aid rather than assuming every serial is globally unique or that an exact match proves the physical items are identical. Preserve unknown or unreadable identifiers without inventing serials; mark matching confidence accordingly.

## Claims and evidence

Entering an item creates a self-declared ownership claim. The app records who made it, when it was entered, the claimed effective date, and supporting evidence. It must not label the claim as proof of title or ownership verified by a manufacturer.

Keep evidence labels separate:

- Self-declared owner.
- Acquisition document attached, with any review identified separately.
- Transfer confirmed by sender and recipient.
- Label/serial physically checked by an identified person, if this workflow is introduced.

Checking a serial is not confirming ownership or airworthiness. Recording possession, borrowing, renting, storage, rig assembly, and ownership are different relationships. A rigger can document work without becoming the owner.

An initial claim begins history in the application. Earlier history remains unknown unless explicitly supplied with its source; it is not reconstructed as a verified chain.

## Transfer workflow

1. The recorded claimant selects the component(s), recipient, and proposed transfer date. An optional document can be attached.
2. The application creates a pending transfer. An invitation to someone without an account remains pending until they can identify themselves and respond.
3. The recipient reviews the identifiers and selected shareable history, then accepts or declines. Sending an invitation alone does not complete a transfer.
4. Acceptance creates a dated transfer event and ends the sender's active claim for those items, while preserving the history and attribution.
5. A cancellation, expiry, or refusal leaves the original claim in place. Repeated submissions must not duplicate a completed transfer.

Transferred items retain serial and attributable service history. Private purchase prices, receipts, owner identities, contact details, and unrelated notes do not become available to later owners automatically. Define a field-level disclosure policy before implementation. A completed transfer's correction needs an attributable event or dispute workflow rather than silent rewriting.

## Duplicate claims and disputes

If a matching identifier is already recorded, do not grant ownership to the new claimant or disclose the existing claimant's identity. Explain that the identifier needs review. Possible causes include typing errors, reused identifiers, an unrecorded sale, or a contested claim.

Support a private resolution process with evidence and correction history. The app must not adjudicate title automatically, award ownership to the first registration, or delete prior history when a duplicate appears. Competing accepted transfers and simultaneous claim updates require consistent handling.

Optional later feature: an owner-reported lost/stolen status with attribution, dates, correction, and dispute handling. This is a report, not an official theft determination. Public lookup and notifications need a separate design; they are not assumed in the initial proposal.

Additional research found [USPA's public stolen-gear reports](https://www.uspa.org/information/news/stolen-gear). Linking to reports is a candidate convenience; automated access and current coverage have not been established. A missing match cannot validate ownership. See [integration opportunities](integration-opportunities.md).

## Privacy and access

Full serials, ownership identities, receipts, and contact details are private by default. Allow the user to share a limited equipment summary with a buyer, rigger, or dropzone. Avoid an enumerable public directory that reveals serial/owner associations.

Define retention, account deletion, sharing revocation, and what prior participants retain after a transfer. Prior transaction history must not give a former owner access to the recipient's future private notes or location. A voluntary share must show exactly which records and people are included.

## Acceptance examples for future implementation

- A jumper records a main and reserve with independent serials; moving the main into a different container preserves its identity and ownership history.
- Adding a receipt leaves the claim self-declared unless a separate review actually occurs.
- A pending sale does not change the active recorded claimant. Recipient acceptance records the transfer once.
- Transferring a main canopy does not transfer the rest of the rig or every attachment in the seller's account.
- A label check and a maintenance entry identify the checker and scope without certifying ownership.
- Duplicate registration does not expose another person's identity or overwrite their claim.
- A serial correction preserves the earlier value and flags any effect on item matching or pending transfers.

## Open discovery questions

- Which equipment types and manufacturers should be covered first, and how are their serials structured?
- Is the first need a private inventory, a transfer history, or both?
- What evidence would users and prospective buyers find useful, and what would they be comfortable sharing?
- Who can review claims, correct mistakes, and resolve contested records?
- How should joint ownership, business-owned gear, rentals, gifts, offline purchases, and account recovery work?
- Which documents and identity details follow an item after transfer, and which stay private?
- Would manufacturer/rigger participation improve a later version? None is assumed arranged.

Related: [feature catalog](feature-catalog.md), [adoption strategy](adoption-strategy.md), and [needs discovery](needs-discovery.md).

## Implemented in #152

Backend `backend/app/skydiver/gear/` (`/api/skydiver/v1/gear/...`); web `/gear` and `/gear/{id}` under Records. Owner-only throughout.

| Area | Behaviour |
| --- | --- |
| Components | Container/harness, main, reserve, AAD or other, each with its own ID. Required: type and label. Optional: manufacturer, model, serial, manufacture date, notes. The serial is stored exactly as typed (case, leading zeros, punctuation; only edge spaces trimmed). Manufacture and acquisition dates keep their precision: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, never a guessed day, never in the future |
| Relation and acquisition | Owned, borrowed or rented, chosen by the owner. Acquisition method (purchase, gift, inheritance, other) and date apply only to owned items. Every response carries `provenance: self_reported`; nothing says verified, title or airworthy |
| Rigs | Named assemblies with dated membership (`from`, exclusive `until`). Moving a component closes the old stint on the move date and opens the new one; moves cannot be backdated before the current stint or set in the future (the latest calendar date anywhere, UTC+14, counts as today). Archiving a component or a rig ends current stints today and keeps history |
| Servicing | Entries the owner records: repack, inspection, maintenance, AAD service, other; done date, optional due date and "done by" text. Labelled as the owner's own entries; the gear list shows the latest due date entered, with no overdue/airworthy status |
| Jump limit | One optional limit per component that the owner sets (a number of jumps, a label such as "Reline", and the service kind that restarts the count; default maintenance). It counts the owner's jumps linked to the component after the day of the latest service of that kind, or all linked jumps when there is none. "Due soon" when within 10% of the limit or 25 jumps (whichever is fewer), at it or over it. No manufacturer figure is ever filled in; one limit per component for now (more would need a small table) |
| Corrections | Each change is a private history event. Changes to identifying fields (type, label, manufacturer, model, serial, dates, relation, acquisition) keep the earlier value; notes record only that they changed |
| Privacy | Serials are compared only within the owner's own gear (a "same serial" note links the owner's other items). No lookup across accounts exists, so another person's claim is never revealed, matched or overridden, and recording a serial confers nothing |
| Safety of writes | Creates and service entries carry a client key, so a retried form does not duplicate. Edits send the version they were based on; a stale edit gets `edit_conflict`. Limits: 50 components, 20 rigs, 100 service entries per component (working defaults; counts are checked without locks, so parallel requests by the same owner can overshoot slightly) |

Not built: photo/document evidence (no hosted media in the beta), transfers, duplicate-claim review across accounts, lost/stolen reports, sharing a gear summary, and links from jumps to components (#153; deleting a component will then be refused once a jump references it, archive instead). Restore/export of gear is #155.
