# UX Polish — Observations from staycation.exe Reference

**Reference image:** `docs/superpowers/specs/refs/staycation-exe.jpg` (committed alongside this note).

This is a follow-up addendum to `2026-05-06-ux-polish-smoother-nes-design.md`, locking in concrete values now that the staycation.exe screenshot has landed.

## What the screenshot shows

A "schedule" / activity-tracker view titled `STAYCATION.EXE` with `▸ RETRO_GAMING_TRACKER — 0/22 CLEARED`. A 4-tab bar (Schedule / Now Playing / Stats / Settings), a 2-button day selector (Thursday / Friday), a section header `▸ Day Session`, and a vertical stack of game-session cards with platform badges (`NES`, `SNES`).

## Confirmed direction: **A. "Console-cased" with phosphor-green / cyan accents**

Direction A from the parent doc is the right pick. The screenshot pins the specifics — the polish answer is more aggressive than I'd guessed, with **rounded corners**, **flat (no-offset) cards**, and a **green-phosphor-plus-cyan accent system** rather than the NES red/yellow palette we shipped.

## Pinned specs (vs current marathon_app NES restyle)

### Palette

| Token | Current (NES) | Staycation-informed | Notes |
|---|---|---|---|
| `bg` | `#0d0d12` | `~#0e1320` | Slightly more navy-blue, less black |
| `bgPanel` / `bgCard` | `#11142a` | `~#1a1f33` | Lifted ~10% from page bg, gives card elevation without shadow |
| `accentRun` (primary action) | `#5cd86c` (NES green) | `~#22d36a` (phosphor green) | Brighter, more "screen glow" feel; same role |
| `accentRest` / secondary | `#5b8cff` (blue) | `~#7ec8c8` (cyan) | Cyan replaces blue for icons + section headers |
| `accentDanger` | `#e84a4a` | unchanged | Still saturated red — reserved for badges + danger CTAs |
| `accentStrength` | `#e8a23a` | repurposed as `accentBadge` | Badge backgrounds (orange/red for one tier, purple for another) — see below |
| `ink` | `#f4f4ec` | `~#e8e8d8` | Slightly warmer cream |
| `inkDim` | `#9a9aab` | `~#8b9bb3` | Cooler grey, leans cyan-tinted |
| `line` | `#000000` | `~#2a3045` | **Critical:** drop pure black borders for soft dark slate |

### Typography

- **Pixel font (`PressStart2P`)**: keep, but **display-only** — title bars, card titles, tab labels, badges, key buttons. Sizes 10–14 only. **Stop using it at 8pt for body labels** — that's the readability complaint baked into the current restyle.
- **Body mono**: VT323 stays for now but the screenshot's body looks more like a clean square mono (e.g., JetBrains Mono / Fira Code / Geist Mono). Lower priority swap. If/when we change, JetBrains Mono via `expo-font` is the cheapest route.
- **Section headers** (`▸ Day Session` style) — mixed-case mono in cyan, **not pixel font, not all-caps**. Section heads in the current app are mostly all-caps pixel — this swap alone makes a big legibility difference.

### Borders & elevation

- **Corners:** `4px` radius on cards and pills (currently `0`). Active-state pills get `~6px`. NO sharp 0-radius elements in the chrome anywhere.
- **Border weight:** `1px` (currently `2px`).
- **Border color:** soft slate `~#2a3045` (currently pure `#000`).
- **Drop shadow:** **remove the offset hard shadow entirely**. Cards are flat. Elevation comes from the slightly-lifted background tone (`bgPanelAlt`) plus the soft border. This is the single biggest visual delta from the current look.
- **Active button:** solid filled accent color, rounded, no border. The current "translate-2px on press" mechanical feel can stay — it's a nice signature — but only on PRIMARY buttons.

### Badges

The screenshot's `NES` (red) and `SNES` (purple) pills are a great precedent for our family pills. Map:
- Running → keep accentRun, but pill rather than pixel (already pill-ish via `RetroPill`).
- Strength → red badge (`#e8593a` ish).
- Cross/rest → purple badge (`#7c5cd8` ish).
- Pixel font, ~3–4px radius, ~6px horizontal padding, 1px line height matching content.

### Spacing & rhythm

The screenshot uses generous vertical rhythm — cards have ~14–16px internal padding and ~12px gap between cards. The current `WorkoutCard` pads at 12 with 14px gap; bring those up by ~2px each. Section headers get ~24px breathing room above.

### What stays explicitly NES (the "matrix/gameboy feel in some areas" the user asked for)

- The brand title (`MARATHON` / `STAYCATION.EXE`) — pixel font, phosphor green
- The `▸` cursor caret on section headers and active states
- The `[ PLANNED ]` style brackets on status pills (we may consider rounded badges instead, but the bracket convention is the matrix nod)
- Tab bar labels (pixel, all caps)
- Step-easing on the press animation for primary buttons
- Family-color accent dots on cards

### What goes smoother

- Card frames (rounded, soft borders, flat)
- Drop shadows (gone)
- Body type (mono, mixed-case, breathing room)
- Section headers (cyan mixed-case, not pixel-all-caps)
- Color saturation outside data (chrome cools/desaturates; data colors stay vivid)

## Implementation order (small enough for one focused commit-set)

1. `theme/tokens.ts` — palette adjustments (bg shift, line color, cyan introduction, ink warming)
2. `theme/retro.ts` — `nesBorder` becomes `softBorder` (1px, slate), `nesShadow` becomes `noShadow` (or removed at the call sites)
3. `RetroBorder.tsx` — radius 4, soft border, no shadow
4. `RetroButton.tsx` — radius 4–6 by tone, no border on primary, keep press-translate
5. `RetroPill.tsx` — convert to filled-rounded badge variant (status pill stays bracketed for the matrix nod)
6. Section-header pattern — extract to a small `SectionHeader` component using cyan mixed-case mono with `▸` caret; replace existing all-caps pixel headers across screens
7. Smoke each screen, adjust per-screen padding rhythm

Estimated effort: half a day on top of the existing scaffolding.

## Out of scope (for this polish pass)

- Body font swap (VT323 → JetBrains Mono) — defer to a separate pass if needed
- New iconography (the screenshot uses a controller icon on the active tab; we'd need an icon library)
- Animation overhaul beyond the press feel
- Dark/light theme split — staying dark-only

## Done criteria

- All cards / sheets render with 4px-rounded soft-bordered chrome, no offset shadows
- Pixel font is gone from anything below 10pt
- Section headers are cyan mixed-case mono with `▸` caret
- Family/status badges are filled-rounded with the new color mapping
- Side-by-side comparison with the staycation reference looks like a sibling, not a stranger
