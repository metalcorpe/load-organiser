# Graphite look (design H) — short design

Owner request, 2026-11-25: make the app "look more fresh and modern". The owner could not name a cause and
pointed at the dark theme. From browser mockups (Discover and an event page, dark and light) the owner picked
**D1 Graphite** and approved a light theme that follows the same rules. The approved mockup is kept at
`docs/product/mockups/graphite-look.html` (an HTML fragment; open it in a browser).

Reviewed before building by Codex (read-only, 2026-11-25); its corrections are folded in below.

## Intent

The layout, tabs, fonts and content are liked; the surface feels dated. In dark that is mostly the navy
background and the bright blue `--border` (`#3a5780`) on cards, chips, dividers and the tab bar. The fix is a new
surface treatment in both themes, not a redesign.

## Goals

- Dark: neutral near-black page (`#111214`), cards one shade lighter (`#1c1d21`), no visible outlines on cards,
  chips or the tab bar.
- Light: neutral light grey page (`#f5f5f7`), white cards with a soft shadow instead of a visible border.
- Phone tab bar: a floating rounded bar inset from the screen edges, above the iPhone home indicator; the active
  tab is a filled pill (see "Active tab" below).
- Light and dark feel like one app: the same rules, different values.

## Non-goals

- No layout, navigation, copy or font changes. Outfit and Figtree stay.
- The per-type event colours stay (boogie, camp, course, event); their dark backgrounds may be retuned to sit on
  graphite.
- The large-screen (48rem and up) navigation stays a static top bar; it gets the new colours and the same active
  pill, not the floating shape.

## Anti-goals (fails even if it "works")

- Any text or control under WCAG AA contrast, in either theme.
- Form fields that are hard to find. Fields already use `--field` and `--field-border` (`web/src/app.css:232`,
  `:311`, `:376`); they keep a visible edge with a 3:1 non-text contrast. No new field token.
- Keyboard focus that is harder to see than today.
- Boundaries that vanish in Windows high contrast (forced colours).
- The floating tab bar covering content, the Discover "Apply" bar or the home indicator, or losing its 44px
  tap targets.

## Approaches (owner picked 2)

1. **Tokens only.** Recolour `light.json`/`dark.json`, fade `--border`. Low risk, but no shadows and no floating
   bar: a recoloured version of today, not the approved look. Rejected.
2. **Tokens plus a component pass.** New colour values, an elevation token, then review each of the 55
   `var(--border)` uses in 33 files (borders, but also some shadows and a gradient divider) and the tab bar.
   **Picked.**
3. **Redesign components from scratch.** The layout is liked; more risk without changing what the owner sees.
   Rejected.

## The design

- **Tokens** (`web/src/lib/design/tokens/`): new values for `bg`, `surface`, `surface-soft`, `fg`, `muted`,
  `border`, `field`, `field-border` in both themes, and a review of `accent`, `accent-soft`, `focus`,
  `highlight`, `brand`, `brand-fg`, `brand-muted` and the warn/ok/bad and event-type pairs against the new
  surfaces. New: `shadow-card` (light: two-layer soft shadow; dark: a 1px inset top highlight) and `nav-bg`
  (an opaque colour; translucency with `backdrop-filter` only inside `@supports`, so contrast is checked on the
  opaque value). Dark `field` stops being navy. File descriptions become "Design H (graphite)".
- **Brand surfaces** move off navy to deep graphite (dark) and near-black (light). Consumers: `+layout.svelte`
  (account avatar), `ExploreSwitch`, `FeaturedListing`, the event page hero, Logbook summary, jump page, profile,
  history. Each is looked at in both themes.
- **Borders:** card-like containers and chips keep `border: 1px solid` but with `transparent` colour (plus
  `shadow-card` on cards). A transparent border keeps the box size unchanged and is drawn in forced-colours mode,
  so boundaries survive Windows high contrast without extra rules. Kept visible: field edges, warning/semantic
  borders (`app.css:421`), side rules that carry meaning (`DueList.svelte:44`, overdue colour), and faint
  dividers between rows inside a card (price list, listing details). Hover outlines (`ListingItem.svelte:75`)
  stay, retuned to the new palette.
- **Active tab (owner confirmed 2026-11-25: neutral, as mocked):** a filled pill: light pill with dark text in dark mode, dark pill with white text in light mode,
  as in the approved mockup. The orange top bar on the active tab goes. In forced colours the active tab keeps a
  visible marker (`Highlight` background via `@media (forced-colors: active)`), since a background pill alone is
  removed there.
- **Floating tab bar (phones only):** inset 12px left/right; bottom offset 12px + `env(safe-area-inset-bottom)`;
  radius 20px; no safe-area padding inside the bar. Add `viewport-fit=cover` to `app.html` so the safe-area value
  is real on iPhones. One custom property for the clearance (bar height + offsets) replaces the separate values
  in the layout footer (`+layout.svelte:90`, `:278`), the global scroll padding (`app.css:23`) and Discover's
  sticky Apply bar and scroll padding (`+page.svelte:424`). The bar renders only for members; guest pages keep
  no clearance.
- **Storybook:** `Foundations.mdx` lists only colour tokens in its `ColorItem` swatches; `shadow-card` gets its
  own small sample.
- **Docs:** `docs/product/mobile-journeys.md` notes design H replaced E/G.

## Tests to add or change

- `tokens.spec.ts`: pairs for `nav-bg` with tab text, the active pill (both themes), `field-border` against the
  new `bg`/`surface`/`field`, and the retuned brand and event pairs.
- e2e: the existing Discover "Apply above the tab bar", desktop stable tab bounds and 44px target tests must pass
  unchanged; add one phone check that the last item on a long page can scroll fully clear of the floating bar.
- axe light and dark as today.

## Left to the builder

- Exact values beyond those above, as long as contrast passes and they match the mockup.
- Which in-card dividers stay as faint lines.

## Checks

`scripts/verify.sh backend web storybook e2e`, then a manual pass on the local stack at 320/390/768/1440 px in
light and dark, keyboard focus included. Forced colours checked with Chromium's emulation.
