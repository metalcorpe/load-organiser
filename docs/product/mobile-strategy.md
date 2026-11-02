# Mobile-first delivery

Status: working delivery direction following the product owner's preference for a mobile-friendly page. Begin with a responsive website designed for phones. Installable PWA capabilities and separate native applications remain later options; no implementation has been started.

## Proposed starting point

Build a mobile-first responsive SvelteKit/TypeScript website. Keep public discovery and shared links usable directly in a browser without installation or signup. Use the same FastAPI backend for phone and desktop views. Prioritize readable layouts, touch controls, straightforward navigation, and reliable online saving.

React remains the current implementation. The product owner selected the [SvelteKit direction](svelte-transition.md); responsive-web delivery and deferred native/PWA scope remain unchanged. No frontend migration has been performed.

Installation, service-worker caching, offline drafts, background sync, and push notifications are not initial delivery commitments. Evaluate PWA features later if they solve observed needs, and native distribution later still if a concrete device requirement or adoption friction justifies it. A responsive website alone does not provide offline operation.

This recommendation is intended to limit simultaneous delivery/maintenance work given the expense-coverage goal. It is not a measured comparison of user acquisition, retention, or total development cost. No mobile/PWA implementation or device testing has been performed.

The [mobile journey walkthrough](mobile-journeys.md) now gives a concrete proposed navigation, screen sequences, privacy/error states and a clickable design artifact. Its checks do not establish implementation/device acceptance.

## Phone-oriented workflows

- Browse following activity, venues, events, and providers using readable cards and filters.
- Open shared venue/event/activity links directly and preserve the intended destination after login.
- Log a jump with sensible defaults, recent DZ/gear selection, minimal typing, and clear save state.
- Review a share card and its audience; make logging privately as easy as sharing.
- Save opportunities and keep dated visit plans private; shared intentions are deferred.
- Access personal records and gear details without exposing serials or documents on public profiles.
- Return from an external registration page without losing a personal draft.

Candidate navigation: Activity, Discover, Add Jump, My Records, Profile. Gear can be prominent within My Records; exact information architecture remains open. Desktop should remain useful for historical entry, imports, editing, and later operator tools.

## Offline scope

Deferred candidate scope, not part of the initial mobile-friendly website. Online forms should still handle connection failure clearly and avoid reporting unsaved records as saved.

Installation does not automatically supply offline behavior. Define a deliberate offline slice: cached application shell, selected previously loaded personal records, and durable draft jump entry. Show stale data and pending edits. Reconcile queued writes without duplicates or silently replacing newer server data.

Do not promise complete offline browsing, current weather, profile/credential freshness, new booking acceptance, or an up-to-date social feed. Avoid caching other people's private records indiscriminately; logout and audience changes need a cache invalidation policy.

Local data is not a complete backup. Recovery, export/restore, storage limits, and failed synchronization need explicit design. Operating-system background sync is not assumed reliable; foreground reopening/retry should be sufficient for pending personal drafts.

## Notifications and installation

Later options. The initial website does not need installation prompts or push notifications; social activity can be read when the user visits.

PWA installation depends on the platform/browser. Explain installation when useful rather than blocking the first visit. Follow updates can initially use an in-app notification view; push is a separate opt-in capability with subscription lifecycle, permissions, privacy, and backend delivery requirements.

Apple documents web push for Home Screen web apps on iOS/iPadOS 16.4 and later. This is not universal push delivery from any browser tab. Do not make notifications the only route to important record or event changes. Verify supported devices and actual behavior before making promises.

## When native delivery may be justified

Revisit if representative users require device/Bluetooth connections that do not work acceptably on target browsers, native file/share workflows, supported background capture, or if installation/discovery friction materially blocks useful repeated use. Evaluate platform permissions, battery behavior, data quality, and store obligations for the exact workflow.

Background jump recording and live presence are not part of the proposed social V1. Do not add them merely to justify a native app. A native shell does not reduce backend/storage costs or remove synchronization and privacy responsibilities.

[Capacitor](https://capacitorjs.com/docs) offers a possible path to reuse a modern web application within native iOS/Android runtimes, with device APIs/plugins. This is not automatic native parity, store acceptance, or a zero-maintenance conversion. A native UI framework would be another option, with additional UI implementation work. No route is selected.

## Repository impact and release checks

The inspected frontend has React/Vite dependencies, but no PWA manifest, service worker, or native project was found in the file inventory. Mobile layouts, file handling, keyboard behavior, accessible controls, offline drafts, deep links, and permission handling are untested.

A future release needs real-device checks on the supported Android/iPhone browsers and Home Screen modes, plus desktop regression checks. Test spotty connectivity, expired sessions, failed saves, user switching/logout, audience changes, and restore behavior. Mobile-first means prioritizing these tasks, not shrinking the current dashboard.

## Sources

- [MDN installability](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable): manifest and installation behavior.
- [MDN offline/background operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation): service workers, caching, and background limitations.
- [Apple web push](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers): platform requirements.
- [Capacitor documentation](https://capacitorjs.com/docs): native runtime and web-code reuse.

Technical references checked on 2026-11-02; target-device compatibility and implementation remain untested.

Related: [proposed V1](version-one.md), [social activity](social-activity.md), [stack options](stack-cost-options.md), and [sustainability](sustainability.md).
