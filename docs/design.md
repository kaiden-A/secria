# Design language — secure ledger

Secria should feel like a precise instrument, not a generic SaaS dashboard. The
visual metaphor is a **secure ledger**: ice-white paper, petrol-blue structure,
hairline rules, monospaced keys, and a single signal colour that means “live”.

## Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#F7FBFB` | Page canvas |
| `--paper-2` | `#EFF7F7` | Subtle inset surfaces |
| `--card` | `#FFFFFF` | Cards, dialogs, tables |
| `--petrol` | `#0A3A46` | Primary buttons, nav, headings |
| `--petrol-deep` | `#062A33` | Dark panels, rail, hero headers |
| `--petrol-soft` | `#E3EFF0` | Selected rows, icon wells |
| `--lime` | `#C7F464` | Active nav bar, focus, status, logo |
| `--lime-soft` | `rgba(199,244,100,0.18)` | Focus halo, new/active badges |
| `--ink` | `#0B2229` | Body text |
| `--ink-muted` | `#5A7177` | Secondary text |
| `--rule` | `#DCE9EA` | Hairline borders |
| `--rule-strong` | `#C6DADB` | Input borders, controls |
| `--danger` | `#C34A3A` | Destructive actions, errors |

Signal lime is an **accent**, never a surface. Large lime areas are reserved for
the primary CTA on a petrol panel and the logo keyhole. Everything else uses it
for a 2–3px indicator, a dot, a focus ring, or a status badge.

## Type

- **Sora** — display and headings. Tight tracking (`-0.03em` to `-0.045em`).
- **Manrope** — UI and body.
- **IBM Plex Mono** — secret keys, environment names, metadata, eyebrows.

Eyebrows are uppercase mono with `0.16em` tracking and a lime signal dot.

## Layout

- Landing: sticky ice nav, split hero, petrol ledger mock, four-step flow,
  two-column feature grid, petrol security panel + key-chain diagram, petrol CTA.
- App shell (Phase 7): 264px petrol rail, ice content canvas, slim topbar,
  breadcrumb, workspace switcher, lime active bar.
- Project page: environment tabs with a lime underline, secret table with mono
  keys and masked values, action menu on row hover.
- Dialogs: white cards, petrol header strip, hairline border, soft shadow.
- Mobile: rail becomes a top bar; tables scroll horizontally; dialogs become
  full-width sheets.

## Component classes

`app/globals.css` owns the shared `sc-*` layer. Reuse it; do not add one-off
page styles when a class already exists.

```text
sc-btn / sc-btn--primary / sc-btn--ghost / sc-btn--lime
sc-input / sc-label / sc-field / sc-error
sc-eyebrow / sc-mono / sc-signal-dot
sc-hero / sc-ledger / sc-flow / sc-feature / sc-security / sc-cta
sc-login / sc-login-aside / sc-login-card
```

## Rules

1. Lime is a signal, not a background. One strong lime moment per screen.
2. Petrol carries structure: nav, primary actions, dark panels, headings.
3. Ice white is the canvas; cards are white with hairline rules.
4. Use mono for anything a developer would put in a `.env` file.
5. No decorative gradients except the soft lime/radial glow behind the hero and
   CTA. No glassmorphism beyond the sticky nav blur.
6. Shadows are soft and low-contrast; the design should read as paper and ink.
7. Motion is 120–180ms; respect `prefers-reduced-motion`.
8. Focus rings are visible and use petrol on ice, lime on petrol.
9. Every interactive control has a hover, focus, and disabled state.
10. Never show a secret value by default. Mask it and make reveal deliberate.
