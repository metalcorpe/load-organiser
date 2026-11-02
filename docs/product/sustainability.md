# Sustainability and community support

Status: discovery proposal with a clarified funding objective. The product owner does not seek personal income initially: the platform should cover its operating expenses with room for error. Free individual access, community participation, voluntary support such as Buy Me a Coffee, sponsorship, ads, and later professional revenue remain options. No pricing, funding provider, public pledge, or payment integration has been selected.

Research date for provider information: 2026-11-02. No account setup, outreach, payments, or funding experiments have been performed.

## Proposed direction

Established objective: cover actual operating cash expenses and build a contingency reserve. Personal income is not an initial funding goal. Track unpaid maintenance effort transparently without assuming the support target pays a salary. This objective does not imply an unlimited personal subsidy if funding falls short.

Keep a useful personal core free, offer voluntary one-time/recurring support, allow community contributions, and consider clearly labeled direct sponsorship later. Evaluate paid professional/dropzone services if organizations adopt them and receive operational value.

Avoid the promise “everything is free until dropzones join.” That makes individual access depend on uncertain operator adoption and leaves later pricing unclear. Instead specify which core functions are intended to remain free and which costly or professional services may need limits or separate funding. Any permanent public promise needs a deliberate decision and a feasible budget.

## Funding options

| Option | Fit with stated goal | Trade-offs and unresolved questions |
| --- | --- | --- |
| One-time support | Low-commitment way for satisfied users to contribute | Variable income; cannot be assumed to fund recurring operations |
| Recurring supporter membership | More predictable support without blocking the core product | Requires cancellation handling, clear expectations, and evidence of actual support |
| Direct sponsorship | Gear manufacturers, shops, schools, or other providers could fund a named service or project | Sales/relationship work, dependency on sponsors, and conflict-of-interest boundaries |
| General advertising | Could contribute income if usage and rates justify it | No traffic, fill-rate, revenue, or effect on trust is established; adds implementation and privacy work |
| Optional paid personal extras | Can associate heavy usage costs with users who choose those services | Must preserve a coherent free experience and avoid trapping records |
| Paid professional/DZ tools | Charge organizations for operational value rather than every jumper | Adoption and willingness to pay unvalidated; support obligations can increase |
| Community contributions | Listings, corrections, translations, documentation, and code can improve coverage | Contributions need review; volunteer effort does not pay hosting or remove maintainer responsibility |

Proposal: do not make general advertising a launch dependency. Reassess direct sponsorship after there is actual usage and a clear audience. This is a product judgment, not a revenue forecast.

## Candidate free core and separately funded work

Proposed free core: basic logbook and statistics, personal gear/serial records, standard record export, basic discovery browsing/saving, and basic sharing. Exact import, forecast, attachment, and storage allowances remain undecided.

Potential costly extras: large media storage/streaming, compute-heavy analysis, repeated paper recognition, large import batches, or unusually frequent paid-provider queries. Consider reasonable quotas, bring-your-own links/files, voluntary funding, or explicit paid add-ons before promising unlimited service.

Support must not buy credential verification, acceptance at a dropzone, dispute outcomes, ownership status, or favorable safety/gear notices. A supporter badge, optional acknowledgement, or development updates are possible acknowledgements; no priority-support or delivery commitment is assumed.

If support lapses, a user's existing personal records should remain accessible and exportable. Future allowance changes need a clear notice and retention policy; never use ownership history or logbook export as leverage to force payment.

## Community model

Treat community contribution, financial support, open-source licensing, and governance as separate decisions. A community-driven board can accept sourced submissions and corrections while requiring moderation and accountable ownership. Receiving support does not establish collective control of private records or product decisions.

Candidates: volunteer listing editors, translations, documentation, bug reports, importer fixtures with permission, and optional public acknowledgements. Define roles, review authority, conflicts, abuse handling, and succession rather than relying on an undefined community to run the service.

A sponsor or paying organizer can have a clearly labeled placement or acknowledgement under a published policy. Payment must not imply accreditation, disguise an advertisement as an organic recommendation, suppress relevant notices, or grant access to private logbooks, location history, gear serials, or contact data.

## Support platform observations

- [Buy Me a Coffee terms](https://buymeacoffee.com/terms) list a 5% platform fee plus separate payment processing; payout/currency-related charges may also apply. Evaluate recurring support, supported payout countries, and net receipts before selection.
- [Ko-fi fee documentation](https://help.ko-fi.com/hc/en-us/articles/360002506494-Does-Ko-fi-take-a-fee) distinguishes Free mode's 0% service fee on one-time tips from fee-bearing support types/modes; payment processor fees remain. Account settings matter.
- [Open Collective](https://opencollective.com/fiscal-hosting) is another model for transparent community funding through fiscal hosts. It involves a different organizational arrangement; do not treat it as interchangeable with a tip button or assume a host will accept the project.

These are research leads, not endorsements or a complete cost comparison. Verify current terms, account eligibility, payout arrangements, and all charges before opening a support page. Do not represent voluntary contributions as tax-deductible charitable donations without an established basis.

## Budget and review

### Expense coverage and room for error

Proposed budgeting method, not an approved financial target:

- `C`: measured normal monthly cash costs, including fixed subscriptions, variable usage, and monthly provision for known annual expenses.
- `B`: additional monthly contingency allowance for usage/cost variance; choose after measuring the main cost drivers.
- `R`: desired cash reserve, proposed initially as several months of normal operating costs rather than an arbitrary fundraising total.
- `T`: chosen number of months over which to build that reserve.
- Initial net monthly funding target: `C + B + max(0, R - available reserve) / T`.
- Once the reserve is funded, net recurring coverage should cover `C + B`; reassess the reserve when cost or risk changes.

Available reserve excludes money already committed to unpaid bills. Processor/platform charges reduce receipts, so the public gross-support target needs to yield the required net amount after fees. One-time contributions can seed reserves; they should not be treated as dependable monthly income. No actual costs or target amounts are known yet.

Start within no-payment free tiers where suitable, using provider subdomains and bounded features. Free tiers have quotas, outages, and changing terms; their availability is not a promise of permanent zero cost. Investigate a small public discovery site/demo separately from hosting sensitive user records or dependable operations. Paid trials with eventual charges do not meet a strict zero-budget starting condition.

See [stack and cost options](stack-cost-options.md) for the distinction between framework changes, serverless hosting, and local processing. No rewrite is selected; browser-only records need a recovery/backup design and shared transactions still need authoritative services.

Before enabling recurring paid infrastructure, identify what covers it and how usage can be capped or suspended. Avoid uncapped automatic upgrades. If support falls short, reduce optional costly workloads or pause expansion and communicate the trade-off; do not assume advertising or future DZ adoption fills the gap.

The intended user-facing message is expense coverage and a disclosed buffer, not a salary goal or a promise of a financially guaranteed service. Publish actual costs, net receipts, and reserve progress at a useful cadence without exposing private payment data.

Track actual hosting/database/backups, storage/bandwidth, weather/other providers, email/notifications, processing fees, moderation/support, and maintenance effort. Distinguish cash expenses from unpaid labor and the maintainer's personally funded contribution.

Use actual net receipts: recurring support + one-time support + sponsorship + optional service revenue − ongoing cash costs. Record occasional migration/development costs separately. No user-to-support conversion rate, ad yield, operating cost, or break-even point is known.

If publishing a funding target, tie it to measured costs, describe what is covered, and report shortfalls honestly. Avoid implying recurring costs are securely funded by a single good month. Define what happens if support cannot cover costs: reduce optional expensive functions, seek targeted sponsorship, reconsider pricing, or communicate a sustainable maintenance scope.

## Questions before commitments

- Which cash expenses are required at launch, and what contingency allowance/reserve is appropriate? Personal income is outside the initial funding goal.
- What personal functions should remain free, and what allowances keep them affordable?
- Would users choose recurring support, one-time tips, or optional paid capabilities?
- What community responsibilities can be reviewed and maintained reliably?
- Which sponsorship placements, if any, fit the experience without compromising trust?
- What professional services could later have a separate price without changing the personal core?

Related: [adoption strategy](adoption-strategy.md), [connected product model](product-model.md), and [roadmap](roadmap.md).
