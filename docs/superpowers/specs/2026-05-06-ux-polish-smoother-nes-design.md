# UX Polish — Smoother NES (Three Directions)

**Status:** design draft (awaiting reference screenshot)
**Date:** 2026-05-06
**Owner:** session lead (CBell)
**Branch target:** `session-2/backend-move-endpoints` (doc only)
**Code changes:** none in this pass — this is a design-mode artifact

## 0. Brief

We just shipped a full NES-classic retro restyle (commits `ee63b0d` →
`43ebf4f`). The user likes the direction but wants to "polish it up" toward
a `staycation.exe` reference: smoother lines while preserving a
matrix/Game Boy feel in places. The reference screenshot was not
attached — this doc proposes three polish directions without committing
to a specific staycation.exe aesthetic. A second pass will pin the
direction once the screenshot is in hand.

## 1. Audit of the current NES look

Anchored in actual files on `session-2/backend-move-endpoints`.

### 1.1 Tokens — `mobile/src/theme/tokens.ts`

- `colors.line` is **pure black `#000000`** (line 10). Combined with the
  navy panel `#11142a`, the contrast ratio is roughly **15:1** — visually
  correct for NES dialog frames but reads as harsh on a 6" OLED. Borders
  punch holes in the composition rather than holding it.
- Accents are **fully saturated NES tones** (`#5cd86c`, `#e8a23a`,
  `#5b8cff`, `#e84a4a`, `#f7d51d`, lines 11–15). They sit at the high end
  of a CRT phosphor palette. Against the navy bg they are loud; the
  yellow `#f7d51d` in particular is the brightest pixel on screen and
  pulls focus from content.
- `radius` is locked at `0` for every size token (line 22). Zero rounding
  is intentional but applies uniformly to *every* surface — buttons,
  cards, inputs, sheets — so we lose the ability to differentiate
  hierarchy via subtle softening.
- `spacing` scale (line 19) tops out at `xxl: 32`. Most card padding is
  `12` or `14` (see `WorkoutCard` line 42, `RetroCard` `padding=14`). It
  reads as **dense**, not breathable.
- Two fonts: `PressStart2P` (pixel, headers/buttons) and `VT323`
  (terminal mono, body). `VT323` at 14–22pt is fine; `PressStart2P` at
  **fontSize: 8** (used for status pills, micro-labels, in-card buttons
  in `WorkoutCard.tsx` lines 48, 105, 114) is a real legibility risk on
  smaller phones — every glyph is roughly 6 device pixels tall before
  scaling.

### 1.2 Primitive — `RetroBorder` (`mobile/src/components/retro/RetroBorder.tsx`)

- Wraps every card with `nesBorder()` (2px solid black, 0 radius) +
  `nesShadow()` (2px hard offset, opacity 1, no blur). On stacked
  elements (the COACH BRIEF panel, then a list of WorkoutCards in
  `TodayScreen.tsx` lines 77–118) you get a **shadow stack**: each card
  drops a hard black brick under the card below it. It's authentic NES
  dialog-box vocabulary, but it **flattens spatial hierarchy** — every
  surface looks "popped" the same amount.
- Background defaults to `colors.bgPanel` (`#11142a`); the inner panel
  and the screen bg `#0d0d12` are nearly the same value, so the border
  is doing 100% of the panel/bg separation. Soften the border and the
  panel disappears.

### 1.3 `RetroButton` (`mobile/src/components/retro/RetroButton.tsx`)

- Mechanical-press effect (lines 49) — `translate 2px` on press,
  shadow drops. **This works.** It's the most successful NES detail in
  the codebase; keep it across all directions.
- All-caps `PressStart2P` at fontSize 10 (line 59). Readable on primary
  CTAs, marginal on small inline buttons.
- `tone="primary"` paints the button with `accentRun #5cd86c` — bright
  green on black border, ink color is `colors.bg` (near-black). The
  contrast pops, but the saturation is loud. Consider a slightly
  desaturated green for primary CTAs.

### 1.4 `RetroPill` (`mobile/src/components/retro/RetroPill.tsx`)

- `[ PLANNED ]` bracketed label, **fontSize: 8 PressStart2P**. Bracketed
  status indicators are **the single best detail** in the current
  language — they read as terminal output, give the right "data
  inspector" feel, and survive any palette shift. Preserve in all
  directions.

### 1.5 `RetroCard` + `WorkoutCard`

- `RetroCard` is a thin wrapper around `RetroBorder` + 14px padding
  (`RetroCard.tsx` line 11–18). Fine.
- `WorkoutCard` packs **a lot** into a 12px-padded box: family chip,
  type label, status pill, big title, "was:" tag, four stat tokens, two
  buttons (`WorkoutCard.tsx` lines 39–122). It feels cluttered. Most of
  the secondary info (`distance`, `duration`, `pace`, `hr_zone`) shares
  one color (`inkDim`) and one font, so it reads as a **wall of mono**
  rather than a structured stat row.
- Inline buttons (`WHY?`, `EDIT`) at lines 99–116 are hand-rolled — they
  bypass `RetroButton`, use 2px black borders, no shadow, no
  press-feedback. Visually inconsistent with the primary CTAs.

### 1.6 Screens — `TodayScreen.tsx`, `LoginScreen.tsx`

- **TodayScreen** (lines 64–69): the `▸ TODAY` micro-eyebrow (8pt) and
  the `WHAT'S ON TAP` title (14pt) work as a hierarchy. The
  `▸` arrow is a great cheap retro detail. Keep across directions.
- The COACH BRIEF panel (lines 77–86) is a `RetroBorder` with italicized
  `VT323` body text — the italic + mono looks like leftover terminal
  log, not a coach voice. It's where the NES feel **gets in the way**.
- **LoginScreen** (lines 40–51): the `MARATHON` wordmark in `PressStart2P`
  24pt yellow + `▸ PRESS START` subtitle is genuinely charming. This is
  one of the spots where the NES feel **succeeds completely**. Preserve.
- Inputs (lines 56–68 / 73–83) wrap a `TextInput` in a `RetroBorder`. The
  border is doing focus + container duty simultaneously; there's no
  focus state. With `VT323` 18pt ink the typing experience is fine, but
  there's no visual feedback when a field is active.

### 1.7 `EditQuestSheet.tsx`

- Sheet header `EDIT QUEST` in 14pt yellow `PressStart2P` (line 77) — top
  tier. Best example of pixel-font-as-display in the app.
- Quick-pick grid (lines 89–115): 8-cell grid, 47% wide, hand-rolled
  borders. Selection state flips border + bg to `accentRun` and ink to
  `colors.bg`. The selected state looks correct; **the unselected state
  is muddy** — `bgPanelAlt #1a1d3d` with black border, very low contrast.
- "Tweak stats" expander (line 117–137): nested `RetroBorder` around
  inputs. The inputs themselves have an extra inner 2px black border
  (lines 128, 131, 134) — that's **three concentric black lines** by the
  time you reach the cursor. Border-on-border-on-border. Brutalist.
- Bottom sheet `borderTopWidth: 2, borderColor: black, borderRadius: 0`
  (line 73). Sheet has no rounded top edge; the slide-up reads as a
  panel snapping into place rather than a soft drawer. Loud, but on-brief
  for "NES dialog box."

### 1.8 What works (preserve in every direction)

- `▸` arrow eyebrows
- `[ BRACKETED ]` status pills
- `PressStart2P` for **display only**: wordmarks, sheet titles, tab labels
- The `2px translate` button press effect
- The two-font system (pixel display + mono body) — but cleaner mono for
  body would help

### 1.9 What gets in the way

- Pure black borders on every surface
- Hard 2px shadow on every surface (no spatial hierarchy)
- 8pt pixel font in **content** (status, "was:" tag, inline buttons)
- Saturated yellow `#f7d51d` as a "regular" accent — it's a focus-puller
- VT323 italic for content (looks like terminal noise)
- Three concentric borders inside `EditQuestSheet` tweak panel
- Sheet top has no soft edge — drawer affordance is missing

---

## 2. Three polish directions

For each direction: a one-line philosophy, concrete spec changes, ASCII
mockups of one card and one sheet, and honest tradeoffs.

---

### Direction A — "Console-cased"

> The NES feel survives in the buttons, status pills, and wordmarks; the
> rest gets a soft, modern container language so content can breathe.

**Philosophy:** keep the pixel font as **display-only**, soften everything
else. Borders become dark grey, drop shadows pick up a little blur, and
cards earn a small (4–6px) corner radius. Animations swap step-easing for
gentle springs. The most "polished" of the three; the closest to a modern
app that *happens* to have NES flavor in its accents.

#### Palette adjustments

| Token | Current | Direction A |
|---|---|---|
| `bg` | `#0d0d12` | `#0b0d18` (slightly bluer, more depth) |
| `bgPanel` | `#11142a` | `#171a2e` (lift one step) |
| `bgPanelAlt` | `#1a1d3d` | `#222644` |
| `line` | `#000000` | `#0a0c14` (near-black, not pure black) |
| `lineDim` | — *(new)* | `#2a2e48` (subtle separators inside cards) |
| `ink` | `#f4f4ec` | unchanged |
| `inkDim` | `#9a9aab` | `#a8aabd` (a hair lighter for body legibility) |
| `accentRun` | `#5cd86c` | `#5cd86c` *(primary CTA only)* |
| `accentStrength` | `#e8a23a` | `#e8a23a` |
| `accentRest` | `#5b8cff` | `#5b8cff` |
| `accentDanger` | `#e84a4a` | `#e84a4a` |
| `accentHi` | `#f7d51d` | `#f4d03f` (slightly desaturated, still NES) |

Accents stay NES-saturated but appear in **fewer places** — only on
primary CTAs, status indicators, and family chips.

#### Typography

- `PressStart2P`: **display only** — wordmarks, sheet titles (14–24pt),
  primary CTA labels, tab bar labels, `[ BRACKETED ]` pills. Banned
  below 10pt.
- `VT323`: **gone from body**. Replaced with **JetBrains Mono** (or IBM
  Plex Mono as a fallback — both are loadable via `expo-font`) at 14–16pt
  for body, 13pt for secondary, with proper modern leading
  (`lineHeight: 1.5`). VT323 stays as a stylistic option for the COACH
  BRIEF panel only.
- Letter-spacing: keep `1` on pixel-font headers; **drop to 0** on body.

#### Borders / shadow / radius

- `radius.sm = 4`, `radius.md = 6`, `radius.lg = 8`. Buttons stay `4`
  (just kissed corners), cards get `6`, sheets get `12` on the top edge.
  Status pills, hard pixel UI elements (tab bar) keep `0`.
- Border weight: `1.5px` (use `StyleSheet.hairlineWidth * 3` on iOS),
  color `lineDim #2a2e48` for cards, `line #0a0c14` for buttons. The
  outline is no longer the loudest thing on screen.
- Drop shadow: keep the press-effect on buttons, but cards get a **soft
  shadow** — `shadowColor: '#000'`, `offset: {0, 4}`, `opacity: 0.35`,
  `radius: 8`, `elevation: 4`. iOS-native depth, no NES brick.

#### Buttons

- `RetroButton` keeps the 2px translate-on-press (best detail in the
  app), but the resting shadow is the new soft shadow. Press collapses
  shadow toward `{0, 1}`.
- Tone `primary` desaturates slightly: `#5cd86c` → `#62c97c` (still
  reads green, less neon).
- All-caps + `PressStart2P` 10pt **only on primary CTAs**. Secondary
  buttons get JetBrains Mono SemiBold 13pt sentence-case.

#### Density

- Card padding: `14` → `18`.
- WorkoutCard inner gaps: `marginBottom: 6/8` → `10/12`.
- ScrollView padding: `20` → `20` (unchanged) but `paddingBottom: 40` →
  `48`.

#### Animation

- Replace `Easing.steps(4)` (`retro.ts` line 6) with a **gentle spring**
  (`damping: 18, stiffness: 220`) for sheet snaps and pill entrance.
- Step-easing remains for the **family chip pulse** and the press
  effect — places where a snap feels intentional.

#### ASCII mockup — `WorkoutCard` (Direction A)

```
┌──────────────────────────────────────────────────────┐ ← 1.5px #2a2e48,
│                                                      │   radius 6, soft
│  ▮ TEMPO                                [ PLANNED ]  │   shadow below
│                                                      │
│  Tempo run                                           │ ← JetBrains Mono
│                                                      │   18pt, lh 1.4
│  6 mi   ·   55 min   ·   7:30/mi   ·   Z3            │ ← stat row, 13pt
│                                                      │   inkDim, mid-dots
│  ┌────────┐  ┌────────┐                              │
│  │ WHY?   │  │ EDIT   │   ← PressStart2P 10pt        │
│  └────────┘  └────────┘     thin border, soft shadow │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### ASCII mockup — `EditQuestSheet` (Direction A)

```
╭───────────────────────────────────────────────────╮  ← top edge radius 12
│        ───  (drag handle, inkDim)                 │
│                                                   │
│  EDIT QUEST                          ← Press 14pt yellow
│  currently: Strength A               ← JetBrains Mono 14pt inkDim
│                                                   │
│  QUICK PICK                          ← Press 9pt inkDim, ls 1
│  ┌─────────┐  ┌─────────┐                         │
│  │  EASY   │  │  TEMPO  │   ← unselected: bgPanelAlt #222644
│  └─────────┘  └─────────┘     border 1.5px lineDim, radius 4
│  ┌─────────┐  ┌─────────┐                         │
│  │ ▮ LONG  │  │ INTERVAL│   ← selected: filled accentRun, ink near-bg
│  └─────────┘  └─────────┘     thin radius-4 chip
│  ┌─────────┐  ┌─────────┐                         │
│  │  STR-A  │  │  STR-B  │                         │
│  └─────────┘  └─────────┘                         │
│  ┌─────────┐  ┌─────────┐                         │
│  │  CROSS  │  │  REST   │                         │
│  └─────────┘  └─────────┘                         │
│                                                   │
│  ▸ TWEAK STATS                                    │
│                                                   │
│  ┌─────────────────┐  ┌─────────────────┐         │
│  │     CANCEL      │  │     CONFIRM     │  ← primary tone
│  └─────────────────┘  └─────────────────┘    fills accentRun
╰───────────────────────────────────────────────────╯
```

#### Strengths

- Looks **like a 2026 product** that has NES taste, not an NES game.
- Best legibility (JetBrains Mono body solves the VT323 wall-of-mono).
- Reuses 90% of the existing token structure — low engineering effort.
- Best accessibility outcome — nothing critical sits at 8pt.

#### Weaknesses

- Loses some of the "this thing is a game cartridge" charm that the
  current build has at first launch.
- "Smoother lines" is the main lever pulled; less Game Boy/matrix vibe
  than the user's brief asks for.
- Soft shadows on cards on iOS look great; on Android `elevation` is
  visually different and sometimes flat — needs a per-platform tweak.

---

### Direction B — "Game Boy hybrid"

> A four-tone Game Boy DMG palette holds the whole UI together; NES
> color flashes appear **only** as data: status, family, danger.

**Philosophy:** lean *into* the user's "Game Boy" cue. Pick the four
classic DMG screen tones and use them as the entire chrome palette.
Reintroduce NES saturation only where it carries information — status
pills, family chips, the one yellow accent on the wordmark. Cards get a
**screen-bezel double frame** (outer dark, inner light hairline) — that's
the "still feels like a Game Boy screen" detail.

#### Palette

DMG core (chrome):

| Token | Value | Role |
|---|---|---|
| `bg` (gb-darkest) | `#0f1a1c` | screen bg, deep |
| `bgPanel` (gb-dark) | `#1b2c2c` | card body |
| `bgPanelAlt` (gb-mid) | `#2d4040` | input bg, raised |
| `ink` (gb-light) | `#cfe0c3` | primary text — soft mint cream |
| `inkDim` (gb-light dim) | `#7a9080` | secondary text |
| `inkMute` | `#4a5d54` | placeholder |
| `line` | `#0a1213` | near-black outer frame |
| `lineInner` | `#3d5454` | inner bezel hairline |

Data accents (sparse, NES-saturated, used only on status/family/alerts):

| Token | Value | Role |
|---|---|---|
| `accentRun` | `#5cd86c` | running family chip + DONE status |
| `accentStrength` | `#e8a23a` | strength family chip |
| `accentRest` | `#5b8cff` | rest/cross family chip + MOVED |
| `accentDanger` | `#e84a4a` | SKIPPED, errors |
| `accentHi` | `#f7d51d` | wordmark + key CTA only |

#### Typography

- `PressStart2P`: wordmarks, sheet titles, **brackets-pill text**, tab
  labels. Same headers as today. Allowed at 10pt minimum.
- `VT323` stays — its CRT vibe **is** the Game Boy/matrix feel the user
  asked for. Used at 16–22pt for body, 14pt for secondary. Banned at
  14pt as headers — that's pixel-font territory.
- Modernize VT323 use: `lineHeight: 1.35`, `letterSpacing: 0.2`. Not the
  raw teletype defaults.

#### Borders / shadow / radius

- **Double-frame border** on cards: outer `1.5px line #0a1213` then a
  `1px lineInner #3d5454` set in `2px` from the outer edge. Creates the
  Game Boy "screen inside a console bezel" effect. Implemented as a
  `View` with two nested borders, no shadow.
- `radius` stays at `0` for cards (preserves the bezel feel) but
  **buttons** get `2`. Inputs `2`. Just enough to look manufactured,
  not pixel-perfect.
- Drop shadow: **dropped from cards entirely** — the double frame does
  the lifting. Buttons keep a 1px hard offset shadow `#000` for
  press-feedback (smaller than current 2px).

#### Buttons

- `RetroButton` keeps the press-translate, shadow shrinks to `1px`.
- Primary CTA tone `accentHi` (yellow) instead of `accentRun` — the
  wordmark and the "go" button share the brand yellow. CTAs are louder
  and easier to find. Secondary CTAs are `bgPanelAlt`.
- Label font: `PressStart2P` 10pt, all caps. Same as now.

#### Density

- Card padding: `14` → `16` (slight breath).
- Shadow stack disappears, so card-to-card separation comes from
  `marginBottom: 14` (unchanged) and the bezel itself.

#### Animation

- Step-easing **stays** — the Game Boy feel is mechanical, not soft. The
  whole palette is asking for snappy state transitions. No springs.
- Add a **2-frame pixel "tick" sound** placeholder (haptic only for now)
  on selection, to reinforce the device-feel.

#### ASCII mockup — `WorkoutCard` (Direction B)

```
┌───────────────────────────────────────────────┐  ← outer 1.5px #0a1213
│ ┌───────────────────────────────────────────┐ │  ← inner 1px #3d5454
│ │                                           │ │     2px gap = bezel
│ │ ▮ TEMPO                       [ PLANNED ] │ │
│ │                                           │ │
│ │ Tempo run                                 │ │  ← VT323 22pt mint
│ │                                           │ │
│ │ 6 mi  55 min  7:30/mi  Z3                 │ │  ← VT323 16pt dim
│ │                                           │ │
│ │ [ WHY? ]   [ EDIT ]                       │ │  ← bracketed buttons
│ │                                           │ │     PressStart2P 10pt
│ └───────────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
```

The inline buttons become **bracketed labels** (no border) — they read
as "options on a Game Boy menu screen." Press still uses the translate
effect; the bracket text shifts color from `ink` to `accentHi` on press.

#### ASCII mockup — `EditQuestSheet` (Direction B)

```
┌────────────────────────────────────────────────┐  ← double bezel on
│ ┌────────────────────────────────────────────┐ │     the sheet itself
│ │       ───   (drag handle)                  │ │
│ │                                            │ │
│ │  EDIT QUEST                  ← yellow accentHi
│ │  currently: Strength A       ← VT323 16pt dim
│ │                                            │ │
│ │  ── QUICK PICK ──            ← Press 10pt inkDim
│ │  surrounded by hairlines lineInner         │ │
│ │                                            │ │
│ │  ┌────────┐ ┌────────┐                     │ │
│ │  │  EASY  │ │ TEMPO  │  ← bezel-style chip
│ │  └────────┘ └────────┘    no shadow, radius 2
│ │  ┌────────┐ ┌────────┐                     │ │
│ │  │ ▮ LONG │ │INTERVAL│  ← selected chip:
│ │  └────────┘ └────────┘    accentRun fill,
│ │  ┌────────┐ ┌────────┐    bg-color ink
│ │  │ STR-A  │ │ STR-B  │                     │ │
│ │  └────────┘ └────────┘                     │ │
│ │  ┌────────┐ ┌────────┐                     │ │
│ │  │ CROSS  │ │  REST  │                     │ │
│ │  └────────┘ └────────┘                     │ │
│ │                                            │ │
│ │  ▸ TWEAK STATS                             │ │
│ │                                            │ │
│ │  [   CANCEL   ]   [   CONFIRM   ]          │ │  ← yellow primary
│ └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

#### Strengths

- Most directly answers the user's brief: "matrix/gameboy feel in some
  areas." The whole chrome **is** Game Boy.
- Strongest visual identity of the three — would never be mistaken for a
  generic mobile app.
- Sparse accent palette means status/family colors pop because they're
  the *only* hot colors on screen. Good information design.

#### Weaknesses

- Most opinionated — viable only if the user actually wants the green
  monochrome floor color. If staycation.exe turns out to be a warm
  cream/beige look, this direction misses the reference badly.
- Body text is mint green on dark green: legible but unusual. Some users
  find sustained reading on green tiring.
- Largest token surface area to refactor. Every screen needs a sweep.
- Implementing the double bezel cleanly in React Native means an extra
  wrapper `View` everywhere we use `RetroBorder` — modest but real
  perf/maintenance overhead.

---

### Direction C — "Cyberpunk terminal"

> Dark navy stays, but the accents move to **phosphor cyan + magenta**.
> Mono everywhere; pixel font reduced to tab labels and key buttons.
> CRT-glow shimmer on focused inputs sells the matrix feel.

**Philosophy:** the user said "matrix/gameboy" — Direction B took the
gameboy, this one takes the matrix. Pull the palette toward CRT phosphor
(cyan/magenta + a green that reads as old terminal, not NES Mario green),
keep the navy/dark base, and move from hard borders to **gradient hairlines**.
The pixel font becomes a *garnish*, not the dominant voice.

#### Palette

| Token | Value | Role |
|---|---|---|
| `bg` | `#070912` | deep terminal black-blue |
| `bgPanel` | `#0f1426` | panel, slight glow under |
| `bgPanelAlt` | `#172040` | input, raised |
| `ink` | `#e6f1ff` | primary text — slightly cool cream |
| `inkDim` | `#7d90b8` | secondary |
| `inkMute` | `#4a5778` | placeholder |
| `line` | gradient `#1a2245 → #2a3360` | hairline separators |
| `accentPhos` (new) | `#7af7ff` | primary phosphor cyan — replaces `accentRun` for chrome |
| `accentMag` (new) | `#ff5dd5` | hot magenta — danger/alerts/secondary CTA |
| `accentRun` | `#43e070` | running family — slightly cooler green |
| `accentStrength` | `#ffb454` | strength family — warm phosphor |
| `accentRest` | `#7d8aff` | rest family — cool blue |
| `accentDanger` | `#ff5dd5` | aliased to magenta |
| `accentHi` | `#ffe770` | wordmark only — softer than `#f7d51d` |

#### Typography

- `PressStart2P`: **tab bar labels, primary CTA labels, status pills**.
  That's it. Banned in headers — they go to mono.
- Body & headers: `JetBrains Mono` (or IBM Plex Mono) — **everywhere**.
  Headers are `JetBrains Mono Bold` 18–24pt with `letterSpacing: 1.5`,
  body is regular 14–16pt with `lineHeight: 1.5`.
- Keep `VT323` reserved for the COACH BRIEF panel — it can be the one
  "voice of the coach is a CRT" detail.

#### Borders / shadow / radius

- **Hard borders gone**. Replaced with `LinearGradient` hairlines (1px
  height, gradient `transparent → #2a3360 → transparent`). Cards have a
  top hairline + bottom hairline; no left/right outline.
- Card corner radius `8`. Sheets `16` on top edge.
- Drop shadows replaced with **bottom phosphor glow** on focused
  elements: `shadowColor: '#7af7ff'`, `offset: {0, 0}`, `opacity: 0.4`,
  `radius: 12`. Off when not focused. Inputs glow when focused; cards
  glow only when actively pressed.
- Optional **scanline overlay** (1px horizontal lines, 4% white opacity,
  every 3px) on top of card surfaces — a stylistic choice we can A/B.

#### Buttons

- `RetroButton` becomes `TerminalButton`. Press effect changes from
  translate-2px to a **flash + shrink**: scale to 0.97 + brief phosphor
  glow pulse. Loses some NES character; gains a "terminal command
  executed" feel.
- Primary CTA: `accentPhos` cyan fill, near-bg ink. Secondary: outline
  only, no fill.

#### Density

- Card padding: `14` → `20`. The most generous of the three.
- Lots of negative space. The phosphor glow needs room to breathe.
- ScrollView padding: `20` → `24`.

#### Animation

- Replace step-easing with `cubic-bezier(0.2, 0.7, 0.2, 1)` — a smooth
  but assertive curve. No bouncy springs (would feel too iOS-default).
- Focused inputs get a **subtle brightness pulse** on the glow (4s cycle,
  opacity 0.3 ↔ 0.5). CRT shimmer.

#### ASCII mockup — `WorkoutCard` (Direction C)

```
   ─────────────────────────────────────────────────  ← gradient hairline
                                                        transparent → #2a3360
   ▮ TEMPO                              [ PLANNED ]    ← cyan family bar
                                                        Press 10pt pill
   Tempo run                                           ← JetBrains Mono Bold 22pt
                                                        ink #e6f1ff

   6 mi  •  55 min  •  7:30/mi  •  Z3                  ← Mono 14pt #7d90b8

   [ why ]   [ edit ]                                  ← outline-only buttons
                                                        cyan border, mono 13pt
                                                        sentence case (rare)
   ─────────────────────────────────────────────────  ← gradient hairline
```

No outer rectangle: the card is **two horizontal hairlines top and
bottom**, padding inside. Cards stack vertically and read as
"records in a terminal log."

#### ASCII mockup — `EditQuestSheet` (Direction C)

```
╭═══════════════════════════════════════════════════╮  ← radius 16 top
│       ───  (drag handle inkDim)                   │
│                                                   │
│  > EDIT_QUEST                                     │  ← Mono Bold 22pt
│    currently: strength_a                          │  ← Mono 14pt inkDim
│                                                   │
│  ── quick_pick ─────────────────────────────────  │  ← gradient hairline
│                                                   │
│  ┌────────┐ ┌────────┐                            │
│  │  EASY  │ │ TEMPO  │  ← Press 10pt label,
│  └────────┘ └────────┘    bgPanelAlt fill, radius 8
│  ┌────────┐ ┌────────┐                            │
│  │  LONG  │ │ INTRVL │  ← selected: cyan glow     │
│  └────────┘ └────────┘    underneath, no fill     │
│  ┌────────┐ ┌────────┐                            │
│  │  STR-A │ │ STR-B  │                            │
│  └────────┘ └────────┘                            │
│  ┌────────┐ ┌────────┐                            │
│  │  CROSS │ │  REST  │                            │
│  └────────┘ └────────┘                            │
│                                                   │
│  > tweak_stats                                    │  ← Mono italic accent
│                                                   │
│  ┌─────────────────┐  ┌─────────────────┐         │
│  │  cancel         │  │  CONFIRM ▸      │         │
│  └─────────────────┘  └─────────────────┘         │
│  outline only           cyan fill, glow           │
╰═══════════════════════════════════════════════════╯
```

#### Strengths

- The most modern of the three. Reads as "Linear meets a CRT."
- Best for dense data — Workout detail / Week view will benefit from
  hairline-only separation.
- Most flexible palette — phosphor cyan + magenta are great for charts
  later (Garmin HR zones etc).
- Scanline overlay is a one-line opt-in/out — easy to tune.

#### Weaknesses

- Strays furthest from the Nintendo opening the user said they "like to
  start." Pixel font is reduced to a garnish.
- Phosphor glow on inputs is a real drain on Android perf if naively
  implemented (`shadowOpacity` on `View` is iOS-only; needs a
  `LinearGradient`-backed shim on Android).
- Magenta + cyan on dark navy reads as "developer tool" or "AI startup,"
  not a personal training app — could feel cold for the workout-coaching
  voice.
- Largest visual change from current state. Highest "what just
  happened" risk for the user.

---

## 3. Recommendation

**Default: Direction A — "Console-cased."**

Reasoning:

1. **It honors the user's actual sentence.** "I like the nintendo theme
   to start, but I'd like to polish it up." Direction A keeps the NES
   bones (pixel-font wordmarks, bracketed pills, button press effect) and
   targets the specific things that feel raw (saturated borders, hard
   shadows, 8pt content text, dense spacing). It is **polish**, not
   redirection. B and C are redirections — fun ones, but the user
   explicitly said start from where we are.

2. **Lowest accessibility risk.** Direction A retires `PressStart2P` from
   content text and brings JetBrains Mono into the body. The current
   8pt pixel labels in `WorkoutCard.tsx` (lines 48, 105, 114) and
   `RetroPill` (line 17) are real WCAG concerns; A solves them while
   keeping the pixel font alive on titles.

3. **Lowest engineering effort.** A is a token-and-primitive sweep —
   `tokens.ts`, `retro.ts`, the four `retro/*` primitives, and a font
   load in app entry. Component-level changes are minimal because most
   components consume `RetroBorder` and `RetroButton`.

4. **Stays compatible with the staycation.exe screenshot.** When the
   reference arrives, A's palette and density are the most likely
   superset. If staycation.exe is greener (B) or cyber-er (C), we can
   migrate from A → B/C selectively. Going B→A or C→A would mean
   throwing away more decisions.

**Honest tradeoff acknowledged:** A is the *least visually distinctive*
of the three. If the staycation.exe screenshot turns out to be highly
opinionated (e.g., genuinely a 4-tone Game Boy palette), we should
reconsider B for at least the chrome layer. **Do not commit to A as
final until the screenshot is in and we've sanity-checked.**

**Accessibility notes:**

- `PressStart2P` at 10pt is the floor; ban smaller sizes in tokens.
- Body text uses `JetBrains Mono` 14–16pt with `lineHeight: 1.5`. WCAG
  AA contrast against `bgPanel #171a2e` is met by `ink #f4f4ec` (~14:1)
  and clears AA Large by `inkDim #a8aabd` (~7:1).
- All accents pass AA against the navy background; double-check
  `accentStrength #e8a23a` on `bgPanelAlt #222644` if used as button
  fill.

**Effort estimate (ballpark, post-decision):**

- Token + primitive sweep: **~3 hours**
- Font loading (JetBrains Mono via expo-font): **~30 minutes**
- Screen-by-screen tweaks (Today, Login, Detail, Week, Settings): **~3 hours**
- Sheet polish (Edit, Why, Displaced, Proposal): **~2 hours**
- QA on iOS + Android visual parity: **~2 hours**

Total: ~half a day of focused engineering.

---

## 4. Implementation outline (Direction A)

Token edits in `mobile/src/theme/tokens.ts`:

- Adjust `bg`, `bgPanel`, `bgPanelAlt`, `inkDim`, `accentHi` to A's
  values.
- Add `lineDim: '#2a2e48'`.
- Change `radius` to `{ sm: 4, md: 6, lg: 8, xl: 12 }`.
- Add `fonts.bodyMono = 'JetBrainsMono-Regular'` and a SemiBold alias.

Primitive updates:

- `mobile/src/theme/retro.ts`: rename `nesShadow` to `softShadow`, default
  to `{0, 4}, opacity: 0.35, radius: 8`. Keep a `nesShadow` alias that
  returns the original hard 2px (used only for button press feedback).
  Replace `Easing.steps(4)` with a spring config helper.
- `RetroBorder.tsx`: change border to `1.5px lineDim`, default radius
  `radius.md`, soft shadow.
- `RetroButton.tsx`: keep press translate; resting shadow is the new
  soft. Primary tone = desaturated green `#62c97c`. Add a `size: 'sm' | 'md'`
  prop so secondary buttons can render JetBrains Mono SemiBold 13pt.
- `RetroPill.tsx`: bump font from 8pt to 10pt; preserve brackets.
- `RetroCard.tsx`: bump default padding from 14 to 18.

Screen-by-screen:

- `LoginScreen.tsx`: keep the 24pt yellow `MARATHON` wordmark; swap
  `▸ PRESS START` subtitle from VT323 to JetBrains Mono 14pt; add a
  focused-input state (border lifts to `accentRun` 1.5px).
- `TodayScreen.tsx`: COACH BRIEF italic VT323 → JetBrains Mono Italic
  14pt; bump `paddingBottom` to 48; the `▸ TODAY` eyebrow stays
  PressStart2P 10pt (was 8pt).
- `WorkoutCard.tsx`: replace inline `WHY?`/`EDIT` (lines 99–116) with
  `RetroButton size="sm"` for visual consistency. Stat row uses
  mid-dot separators (`·`) instead of trailing-margin spacing.
- `EditQuestSheet.tsx`: drop the inner 2px borders on inputs (lines 128,
  131, 134) — let the input bg + lineDim outer carry it. Sheet top
  edge uses `borderTopRightRadius: 12, borderTopLeftRadius: 12`.

Animations:

- `Easing.steps(4)` references in sheet snap / pill entry → spring with
  `damping: 18, stiffness: 220`.
- Family chip pulse keeps step-easing (intentional snap).

Out of scope this pass (defer to next):

- Tab bar visual update (verify with screenshot)
- Charts / Garmin HR plot palette (no UI exists yet)
- Sound effects
- Scanline overlay (Direction-C-only flourish; skip in A)

---

## 5. Open questions for the staycation.exe screenshot

When the reference image arrives, these are the calls it will resolve:

- **Exact accent palette.** Is staycation.exe warm (cream/coral),
  cool (cyan/teal), or monochrome (Game Boy)? This is the biggest
  swing between A, B, and C.
- **Specific corner radius.** Are corners truly 0 (NES-pure), 4–6
  (Direction A), or larger (10–14, modern app)?
- **Pixel font: display-only or still in body?** Determines whether we
  retire VT323 or keep it as a whole-app body voice.
- **Drop shadow behavior.** Hard-offset NES bricks, soft modern shadow,
  or no shadow at all? Each implies a different spatial language.
- **Border weight and color.** 1px? 1.5px? 2px? Pure black or tinted?
  This decides whether borders are chrome or ornament.
- **How does staycation.exe handle dense data tables / lists?** Hairline
  separators? Outlined rows? Card-per-row? Drives the WorkoutCard +
  Week view layout.
- **Animation feel.** Does the reference snap (step-easing), spring
  (Direction A), or glide (Direction C)? A 5-second clip would settle
  this.
- **Does the reference have any "screen bezel" or "frame inside a frame"
  device metaphor?** If yes, push B even if the palette is otherwise
  warm.
