# Gear serial numbers and ownership history

Status: proposed extension of F04, prompted by the product owner's question about serial numbers and ownership records. Discovery only; not implemented or an agreed MVP requirement. It can provide individual value without dropzone adoption.

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
