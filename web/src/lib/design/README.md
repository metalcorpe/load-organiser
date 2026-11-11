# Design tokens

Colours, fonts and sizes for design **E** (light) and **G** (dark), chosen by the owner on 2026-11-11.

- Source: `tokens/shared.json`, `tokens/light.json`, `tokens/dark.json`, in the W3C Design Tokens
  Community Group format (`$value`, `$type`, `$description`).
- Build: `npm run tokens:build` runs Style Dictionary (`sd.light.json`, `sd.dark.json` in `web/`)
  and writes `tokens-light.css` (`:root`) and `tokens-dark.css` (`:root` inside
  `@media (prefers-color-scheme: dark)`). Both are committed and imported by the root layout.
  Never edit them or put token values in `app.css`.
- Checks (`tokens.spec.ts`, part of `npm run test:unit`):
  - the committed CSS equals a fresh Style Dictionary build;
  - every text and icon colour pair meets WCAG 2.1 contrast (4.5:1 text, 3:1 large numbers and
    icons), computed with colorjs.io.

Rules the tokens carry:

- `brand` (navy): one pop card or header per screen.
- `accent` (orange): actions (main buttons, active tab, links). `highlight`: key numbers on `brand`.
- Listing types (`boogie`, `camp`, `course`, `event`): a `bg` tint for the date tile and an `fg`
  colour for the tag, always with the type's icon (`TypeIcon`), never colour alone.
