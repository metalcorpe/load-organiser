# USPA integration opportunities

Research date: 2026-11-02. Discovery only. No API access, credentials, agreement, endpoint schema, sandbox, or working integration has been obtained. No outreach has been sent.

## Findings and evidence

### Approved API precedents

USPA's published February 13–15, 2026 board minutes (page 58; PDF cover marked draft) record approval of a Membership Data API request for EZDZ and a single-send, member-opt-in sharing API request for Jumpmaster. They also describe limited approval of a read-only student-data extension pending further review, and a planned Aspire transition to SFTP with details unresolved. These are specific precedents, not confirmation of access or capabilities for this application.

Source: [USPA Winter 2026 board minutes, page 58](https://www.uspa.org/LinkClick.aspx?fileticket=N33gZ6UHKUk%3D&portalid=0).

### Credential checks are access-controlled

USPA's [Credential Check](https://www.uspa.org/check) describes checking individual membership, licenses, and ratings by authorized Group Member dropzones, examiners, and S&TAs, with appropriate account access. The [Group Member benefits](https://www.uspa.org/dz-management/group-membership/group-member-benefits) page describes online credential verification. This is not a public lookup API for every app user.

### Aspire / Merit is another route to investigate

[Aspire's skydiving materials](https://knowledge.merits.com/category/partner/skydiving/) describe the USPA credential relationship and Merit rebranding. Its [integration overview](https://knowledge.merits.com/partner/skydiving/) describes sharing credentials and a BurbleMe connection. These show an existing credential ecosystem; current third-party access, protocols, permissions, pricing, and field coverage need confirmation. Do not assume historic Merit API examples are the current integration contract.

## Candidate capabilities

| Candidate | Proposed user value | Dependency / uncertainty |
| --- | --- | --- |
| Store a membership number and uploaded credentials | Personal document wallet and reminders | Can be self-reported now in concept; uploads must not imply issuer verification |
| Member-authorized credential import | Reduce manual entry and retain issuer-sourced facts | Ask whether the opt-in API precedent can apply to an individual-focused app |
| Membership/license/rating verification | Attributable status for the profile and later operator review | Approved access, exact fields, matching rules, permitted audience, and freshness |
| Aspire credential sharing | Reuse credentials from an existing wallet | Current partner/member-sharing interface and agreement |
| License progress / training evidence | Link personal progression to recognized records | Student API approval, exact scope, authorized audience, and availability unconfirmed |
| Jump-log recognition or official submissions | Potential future convenience for qualification workflows | No logbook sync, writeback, application-submission API, or recognition approval was established |
| Link to official renewal/resources | Help users reach the authoritative service | External navigation, not in-app renewal or SSO |

## Fit with the skydiver-first direction

Investigate voluntary member sharing before relying on Group Member dropzone verification access. Ask whether a consumer app without a partner dropzone can qualify. Keep manual profiles, imports, exports, and personal logging useful if access is delayed or declined.

Design proposed credential records to retain issuer, subject identifier, source, consent scope, retrieval date, expiry where supplied, and source status. Distinguish self-report, uploaded evidence, human review, and issuer-sourced data. A single-send import must not be displayed as continuously synchronized verification.

Membership validity, qualification level, recent jumping activity, and local eligibility are different facts. Credential import does not establish a complete logbook, current practical competence, or acceptance by a receiving dropzone.

USPA integration is not evidence of ownership of a rig or serialized component. No USPA gear-ownership verification API was established in this research; keep [gear ownership claims](gear-ownership.md) and their evidence separate.

## Questions for a future access inquiry

- Can a skydiver-first application obtain member-opt-in sharing access without a participating dropzone?
- Which read APIs are available to which applicant types, and how does approval work?
- Which fields, identifiers, match rules, consent flow, and refresh/revocation behavior are supported?
- What are the fees, usage limits, storage/display/sharing restrictions, retention requirements, and testing options?
- Is student progression available outside the limited project described in the minutes? Is any writeback allowed?
- Should this use direct USPA integration, Aspire, or both, and what has changed since the published minutes?
- What separate process applies to recognition of digital logbooks, signatures, or application exports?

Membership Services and the relevant technology contact are possible starting points through [USPA's official site](https://www.uspa.org/check). Contacting them is a future action; this research does not authorize sending an inquiry.

## Implementation boundaries

No public self-service developer contract was found in the reviewed sources. Do not build against guessed endpoints, scrape the restricted credential utility, collect USPA passwords, or claim an official relationship. Confirm approved access and permitted use before implementing automated retrieval. UI terminology and stale/unavailable-source behavior must match the eventual contract.

Related: [feature catalog](feature-catalog.md), [adoption strategy](adoption-strategy.md), and [market research](market-research.md).
