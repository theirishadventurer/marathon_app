# Feat D — Visual crispness (less 8-bit, more staycation polish)

**Status:** design
**Track:** Session 2.7 — Feature D (parallel with A, B, C)
**Reference:** `docs/superpowers/specs/refs/staycation-exe.jpg`
**Predecessor:** `docs/superpowers/specs/2026-05-06-ux-polish-staycation-observations.md` (Session 2.6 polish)

---

## 1. The brief, in one line

> "We need to make the visuals crisper, similar to the staycation.exe menu options. It still has that retro feel, but its not all 8bit pixel."

We shipped Session 2.6's chrome polish — soft borders, rounded corners, no offset shadows, phosphor-green + cyan palette. The remaining gap is **typography**. PressStart2P (8-bit pixel) is doing every job in the app: brand title, page titles, section headers, card titles, type pills, status pills, button labels, stat labels, day-of-week labels, even error toasts. The staycation reference uses pixel font for **maybe four roles total**: brand, tab labels, platform badges, and a single active CTA. Everything else — card titles, timestamps, descriptions, day selectors — is a **clean square monospace** with weight (Regular / Bold).

That's the swap. This doc plans it.

---

## 2. Audit — every PressStart2P site, classified

23 source files import or use `'PressStart2P'`. Below: every site, with a verdict — **KEEP** (display-only, where pixel-font earns its place) or **SWAP** (content / label, where pixel font hurts legibility).

Legend:
- **KEEP** → stays PressStart2P. Display, brand, badge, key CTA. Sized 10pt or up.
- **SWAP→monoBold** → switch to bold square mono. Card/section/title content.
- **SWAP→mono** → switch to regular square mono. Labels, timestamps, body chrome.

| File:line | Element | Current | Verdict | New family/size |
|---|---|---|---|---|
| `LoginScreen.tsx:41` | `MARATHON` brand title | PressStart2P 24 | **KEEP** | PressStart2P 24 |
| `LoginScreen.tsx:53,70,86` | `EMAIL` / `PASSWORD` / `! ERROR` labels | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `RootNavigator.tsx:31` | Tab icons (glyphs) | PressStart2P 14 | **KEEP** | PressStart2P 14 |
| `RootNavigator.tsx:47` | Tab labels (`TODAY`, `WEEK`, …) | PressStart2P 8 | **KEEP** | PressStart2P 9 (size bump) |
| `TodayScreen.tsx:65,94,102` | `▸ TODAY 5/7` header line, error, REST DAY | PressStart2P 8 | **SWAP→mono** | mono 12 |
| `TodayScreen.tsx:68` | `WHAT'S ON TAP` page title | PressStart2P 14 | **SWAP→monoBold** | monoBold 18 |
| `WeekScreen.tsx:103,116` | `‹` / `›` chevrons | PressStart2P 16 | **KEEP** | PressStart2P 16 |
| `WeekScreen.tsx:109` | `WK 5 / 18` cycle pos | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WeekScreen.tsx:125` | `▸ JUMP TO TODAY` | PressStart2P 8 | **SWAP→mono** (cyan accent) | mono 11 |
| `WeekScreen.tsx:149` | `COULD NOT LOAD WEEK` error | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `ProgramScreen.tsx:67` | `PROGRAM` page title | PressStart2P 16 | **SWAP→monoBold** | monoBold 20 |
| `ProgramScreen.tsx:86` | error | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `SettingsScreen.tsx:135` | `SETTINGS` page title | PressStart2P 16 | **SWAP→monoBold** | monoBold 20 |
| `SettingsScreen.tsx:61,86,134,147,179,191,201` | section labels (`RECONNECT GARMIN`, `LAST SYNC`, `LAST ERROR`, plan name) | PressStart2P 8/10 | **SWAP→mono** (or monoBold for plan name) | mono 11 / monoBold 14 |
| `WorkoutDetailScreen.tsx:30-32` | markdown h1/h2/h3 | PressStart2P 14/12/10 | **SWAP→monoBold** | monoBold 16/14/12 |
| `WorkoutDetailScreen.tsx:67-69` | METRIC/PLANNED/ACTUAL column heads | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WorkoutDetailScreen.tsx:102,111,120` | MATCH CONFIDENCE / DEVIATIONS / ANALYST REVIEW | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WorkoutDetailScreen.tsx:178,189` | `‹ BACK`, `EDIT` header CTAs | PressStart2P 10 | **KEEP** (small CTA, accent green) | PressStart2P 10 |
| `WorkoutDetailScreen.tsx:199,206` | LOADING / COULD NOT LOAD | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WorkoutDetailScreen.tsx:214,219` | `WK n · TYPE` + workout title | PressStart2P 8/14 | **SWAP→mono / monoBold** | mono 11 / monoBold 20 |
| `SectionHeader.tsx:21` | `▸ Day Session` | already VT323 18 cyan | **OK as-is** (Feature C may revisit; this doc leaves it) | — |
| `WorkoutCard.tsx:48` | type pill (`EASY`, `LONG`, …) | PressStart2P 8 | **KEEP** (pill = badge) | PressStart2P 8 |
| `WorkoutCard.tsx:105,114` | `WHY?` / `EDIT` mini-buttons | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WhySheet.tsx:15-18` | markdown h1/h2/h3 | PressStart2P 14/12/10 | **SWAP→monoBold** | monoBold 16/14/12 |
| `WhySheet.tsx:49,57,65` | `WK n · TYPE`, `PRESCRIPTION`, `INTENT` labels | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `WhySheet.tsx:52` | workout title | PressStart2P 14 | **SWAP→monoBold** | monoBold 20 |
| `EditQuestSheet.tsx:77` | `EDIT QUEST` sheet title | PressStart2P 14 | **SWAP→monoBold** (keep accentHi) | monoBold 18 |
| `EditQuestSheet.tsx:86,118,126,129,132` | section labels (`QUICK PICK`, `▸ TWEAK STATS`, `DISTANCE (MI)`, etc.) | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `EditQuestSheet.tsx:106` | quick-pick chip labels (`EASY`, `LONG`, …) | PressStart2P 8 | **KEEP** (these are badges) | PressStart2P 8 |
| `ProposalSheet.tsx:29` | option label (`OPTION A: …`) | PressStart2P 10 | **SWAP→monoBold** | monoBold 14 |
| `ProposalSheet.tsx:36,73,79` | `▸ WHY THIS`, `COACH IS THINKING…`, `PROPOSED REBALANCE` | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `DisplacedSheet.tsx:40,46,61` | `DISPLACED` title, `WHERE SHOULD IT GO?`, `MON…SUN` chips | PressStart2P 12/8/8 | **SWAP→monoBold (title); KEEP for day chips** | monoBold 16 / PressStart2P 8 |
| `DayCard.tsx:24,28,42` | `▸`, day name, `REST` empty-state | PressStart2P 10/10/8 | **KEEP for `▸`; SWAP day name + REST→mono** | PressStart2P 10 / mono 12 / mono 11 |
| `DraggableWeekList.tsx:198,202,222` | same as DayCard — `▸`, day, REST | same | same | same |
| `RetroPill.tsx:32,55` | bracket + badge variants | PressStart2P 8 | **KEEP** (pill = badge) | PressStart2P 8 |
| `RetroButton.tsx:65` | all button labels | PressStart2P 10 | **KEEP for primary tone, SWAP for default/ghost/danger** | see §3.3 |
| `program/StatTile.tsx:19` | stat tile label | PressStart2P 8 | **SWAP→mono** | mono 11 |
| `program/WeekTile.tsx:67` | `WK 05 [PEAK]` | PressStart2P 8 | **KEEP** (it's the badge of the cycle lane) | PressStart2P 8 |
| `program/RaceMilestoneTile.tsx:36` | `⚑ NYC MARATHON` | PressStart2P 14 | **KEEP** (race milestone is celebratory display) | PressStart2P 14 |
| `program/CycleLane.tsx:31` | `P1 NYC` cycle title | PressStart2P 10 | **KEEP** (small, badge-like) | PressStart2P 10 |
| `program/WeeklyMileageTracker.tsx:92` | `P1` / `P2` cycle toggle pills | PressStart2P 8 | **KEEP** (pill = badge) | PressStart2P 8 |

**Net result of swap:** PressStart2P stays in ~12 sites — brand, tabs, badges, pills, key CTAs, race milestone, cycle-lane chrome. PressStart2P **leaves** ~40+ sites where it was acting as content type.

---

## 3. Font swap

### 3.1 Choice

**JetBrains Mono.**

- Free, OFL license, ships Regular + Bold + ExtraBold + Italic.
- Square aperture matches the staycation reference card titles.
- Excellent latin coverage, ligatures off-by-default render fine on RN.
- Already widely deployed in dev tooling, so visual literacy is high.
- File size: Regular ~95KB woff, Bold ~96KB → fine for `expo-font`.

Alternatives considered:
- **Geist Mono** — newer, very crisp, but less complete weights at the time of writing.
- **Fira Code** — too "ligature-y," weights look almost identical.
- **IBM Plex Mono** — softer, slightly more humanist; loses some of the retro grid feel.
- **Space Mono** — too quirky / character-heavy, fights the chrome.

JetBrains Mono is the right pick.

### 3.2 Loading

Drop two files into `mobile/assets/fonts/`:

```
JetBrainsMono-Regular.ttf
JetBrainsMono-Bold.ttf
```

Wire them in `App.tsx` next to existing entries:

```ts
const [loaded] = useFonts({
  PressStart2P: require('./assets/fonts/PressStart2P-Regular.ttf'),
  VT323: require('./assets/fonts/VT323-Regular.ttf'),
  JetBrainsMono: require('./assets/fonts/JetBrainsMono-Regular.ttf'),
  JetBrainsMonoBold: require('./assets/fonts/JetBrainsMono-Bold.ttf'),
});
```

> Note for Feat D engineer: name the family token strings consistently. `JetBrainsMono` (Regular) and `JetBrainsMonoBold` are separate registered families on RN — using `fontWeight` on a single family is unreliable across Android, so we register the bold face explicitly.

### 3.3 Token additions

In `mobile/src/theme/tokens.ts`:

```ts
export const fonts = {
  pixel: 'PressStart2P',   // unchanged — display, badges, brand
  body: 'VT323',           // unchanged for now (CRT/terminal feel for descriptions)
  mono: 'JetBrainsMono',         // NEW — labels, timestamps, body chrome
  monoBold: 'JetBrainsMonoBold', // NEW — card titles, page titles, section emphasis
} as const;
```

We **do not** retire `body: VT323` in this pass. VT323 is still the right voice for markdown descriptions and "feels like a terminal screen" copy (workout description in WhySheet, coach brief). The mono pair is for chrome and content — labels, titles, stats, buttons — i.e., the layer that PressStart2P is currently overworking.

### 3.4 Per-element font assignment table

| Role | Family | Size | Color | Where |
|---|---|---|---|---|
| Brand title | pixel | 24 | accentRun | Login screen `MARATHON` |
| Page title | monoBold | 20 | ink | Program / Settings / `WHAT'S ON TAP` |
| Sheet title | monoBold | 18 | accentHi or ink | EditQuest, Why, Proposal, Displaced |
| Section header | VT323 | 18 | accentCyan | unchanged — `SectionHeader.tsx` |
| Card title (workout) | monoBold | 20 | ink | WorkoutCard, WhySheet, WorkoutDetailScreen |
| Body / description | VT323 | 16–18 | ink / inkDim | markdown body, coach brief, etc. |
| Stat value | VT323 | 22 | ink | StatTile, MATCH CONFIDENCE, planned/actual cells |
| Stat label / chrome label | mono | 11 | inkDim | `LAST SYNC`, `DISTANCE`, `WHY?`, etc. |
| Tab label | pixel | 9 | accentRun / inkDim | bottom tab bar (size up by 1 for parity with staycation) |
| Type pill (`EASY`, `LONG`) | pixel | 8 | family color | RetroPill badge variant on cards |
| Status pill (`[ PLANNED ]`) | pixel | 8 | status color | RetroPill bracket variant |
| Primary CTA | pixel | 10 | bg (on accent fill) | RetroButton tone="primary" |
| Default / danger CTA | mono | 12 | ink | RetroButton tone="default" / "danger" |
| Day name (WED, THU…) | mono | 12 | ink / accentRun-when-today | DayCard, DraggableWeekList |
| Date (12/4) | VT323 | 14 | inkDim | DayCard, DraggableWeekList |
| Cycle-lane week chip | pixel | 8 | bg/ink | WeekTile |
| Race milestone | pixel | 14 | bg | RaceMilestoneTile (celebratory) |

---

## 4. Concrete component changes

### 4.1 Token edits

`mobile/src/theme/tokens.ts`:

- Add `fonts.mono` and `fonts.monoBold` (see §3.3).
- No color, spacing, or radius changes (Feature A may touch radius; this doc stays out of palette/spacing).

### 4.2 RetroButton

`mobile/src/components/retro/RetroButton.tsx`:

| Tone | Family | Size | Notes |
|---|---|---|---|
| `primary` | `pixel` | 10 | unchanged — primary stays pixel for "press start" feel; it's a single short word like "Confirm" or "Apply" |
| `default` | `monoBold` | 12 | swap — labels like "Cancel", "Sync now", "Reconnect" read as commands, not arcade prompts |
| `danger` | `monoBold` | 12 | swap |
| `ghost` | `mono` | 12 | swap |

Also: drop the `.toUpperCase()` on default/danger/ghost. Leave it on primary (per staycation reference, the active CTA is uppercase). Result: `Cancel` reads `Cancel`, not `CANCEL`. This alone halves the "yelling" feeling.

### 4.3 RetroPill — confirm both variants stay pixel

`mobile/src/components/retro/RetroPill.tsx`:

- `bracket` variant (`[ PLANNED ]`): **keep PressStart2P 8**. The bracket is the matrix nod and it's only used at status-pill scale.
- `badge` variant (`NES`/`SNES`-style filled chip): **keep PressStart2P 8**. The reference's `NES`/`SNES` badges are pixel.

No font changes here. Tightness comes from the surrounding swaps making the pill the *only* pixel element on a card, so the pill reads as a category badge instead of disappearing into the text.

### 4.4 WorkoutCard

`mobile/src/components/WorkoutCard.tsx`:

| Line | Element | Before | After |
|---|---|---|---|
| 47-49 | type label `RUNNING` | PressStart2P 8 inkDim | **inside RetroPill badge** — wrap it; `<RetroPill variant="badge" label={type} background={tint+"22"} color={tint} />` (so it actually reads as a badge like `NES`) |
| 56-58 | workout title | VT323 22 ink | **monoBold 20 ink** (the staycation card title is bolder than VT323 body) |
| 64-66 | `↻ was: foo` | VT323 14 inkDim | **mono 13 inkDim** — pairs with new title |
| 75-92 | distance / duration / pace metas | VT323 16 inkDim | **mono 13 inkDim** — these are data labels, not body copy |
| 105, 114 | `WHY?`, `EDIT` mini-buttons | PressStart2P 8 ink | **mono 11 ink**, drop the `borderWidth: 2`, use 1px softBorder, optionally drop the all-caps |

### 4.5 StatTile

`mobile/src/components/program/StatTile.tsx:18-21`:

- Label: PressStart2P 8 → **mono 11 inkDim**
- Value: VT323 22 ink → **monoBold 22 ink** (slight weight bump; numerals look better in monoBold than VT323 at this size)
- Sub: VT323 14 inkDim → unchanged

### 4.6 WeekTile (cycle lane)

`mobile/src/components/program/WeekTile.tsx`:

Keep both lines pixel — this tile is essentially a badge in the cycle lane, and it's tiny. It's actually one of the few places pixel font is doing the right job. **No change.**

### 4.7 RaceMilestoneTile

Keep pixel — `⚑ NYC MARATHON` is celebratory display. **No change.**

### 4.8 SectionHeader

Already VT323 cyan mixed-case. **No change** — Feature C may revisit; this doc leaves it.

### 4.9 WhySheet

`mobile/src/components/WhySheet.tsx`:

| Line | Element | Before | After |
|---|---|---|---|
| 15-18 | markdown h1/h2/h3 | PressStart2P 14/12/10 | **monoBold 16/14/12** |
| 23 | `strong` | VT323 700 | **monoBold 18** (no fontWeight; use the bold family) |
| 49 | `WK n · TYPE` | PressStart2P 8 | **mono 11 inkDim** |
| 52 | workout title | PressStart2P 14 | **monoBold 20 ink, no `.toUpperCase()`** |
| 57, 65 | `PRESCRIPTION` / `INTENT` | PressStart2P 8 | **mono 11 inkDim** |

### 4.10 EditQuestSheet

`mobile/src/components/EditQuestSheet.tsx`:

| Line | Element | Before | After |
|---|---|---|---|
| 77 | `EDIT QUEST` title | PressStart2P 14 accentHi | **monoBold 18 accentHi**, drop the `.toUpperCase()` (it's a verb-noun command) |
| 81 | `currently: foo` | VT323 16 | unchanged |
| 86 | `QUICK PICK` | PressStart2P 8 | **mono 11 inkDim** |
| 106 | quick-pick chips (`EASY`, `LONG`, …) | PressStart2P 8 | **keep PressStart2P 8** — these are badges |
| 118 | `▸ TWEAK STATS` toggle | PressStart2P 8 accentRun | **mono 11 accentRun** |
| 126, 129, 132 | input labels | PressStart2P 8 | **mono 11 inkDim** |

### 4.11 ProposalSheet

`mobile/src/components/ProposalSheet.tsx`:

| Line | Element | Before | After |
|---|---|---|---|
| 29 | option label | PressStart2P 10 | **monoBold 14, drop `.toUpperCase()`** |
| 32 | tradeoff body | VT323 16 | unchanged |
| 36 | `▸ WHY THIS` | PressStart2P 8 | **mono 11 accentRun** |
| 73 | `COACH IS THINKING…` | PressStart2P 8 | **mono 11 inkDim** |
| 79 | `PROPOSED REBALANCE` | PressStart2P 8 | **mono 11 inkDim** |
| 82 | proposal summary | VT323 22 | unchanged |

### 4.12 DisplacedSheet

`mobile/src/components/DisplacedSheet.tsx`:

| Line | Element | Before | After |
|---|---|---|---|
| 40 | `DISPLACED` | PressStart2P 12 accentHi | **monoBold 16 accentHi** |
| 43 | snapshot title | VT323 18 | unchanged |
| 46 | `WHERE SHOULD IT GO?` | PressStart2P 8 | **mono 11 inkDim** |
| 61 | day chips (`MON…SUN`) | PressStart2P 8 | **keep** — day-of-week chips are badges here |

### 4.13 Day headers (DayCard, DraggableWeekList)

`mobile/src/components/DayCard.tsx:22-34` and `mobile/src/components/DraggableWeekList.tsx:196-209`:

- `▸` cursor (when today) — keep PressStart2P 10 accentRun. Cursor is iconographic.
- Day name (`WEDNESDAY`) — **mono 12, drop `.toUpperCase()`** (becomes "Wednesday"). The staycation reference uses cap-mixed weekday labels. Color: `accentRun` when today, `ink` otherwise.
- Date (`12/4`) — VT323 14 inkDim — unchanged.
- `REST` empty-state — **mono 11 inkMute, drop `.toUpperCase()`** → "Rest day".

### 4.14 Page titles & sub-titles

| Screen | Line | Before | After |
|---|---|---|---|
| `TodayScreen.tsx` | 65 | `▸ TODAY 5/7` PressStart2P 8 | mono 12 inkDim |
| `TodayScreen.tsx` | 68 | `WHAT'S ON TAP` PressStart2P 14 | **monoBold 18, drop `.toUpperCase()`** → "What's on tap" |
| `WeekScreen.tsx` | 109 | `WK 5 / 18` | mono 11 inkDim |
| `WeekScreen.tsx` | 125 | `▸ JUMP TO TODAY` | **mono 11 accentRun, drop caps** → "▸ Jump to today" |
| `ProgramScreen.tsx` | 67 | `PROGRAM` | **monoBold 20, drop caps** → "Program" |
| `SettingsScreen.tsx` | 135 | `SETTINGS` | **monoBold 20, drop caps** → "Settings" |
| `WorkoutDetailScreen.tsx` | 178, 189 | `‹ BACK`, `EDIT` | unchanged (small accent CTAs — pixel earns it) |
| `WorkoutDetailScreen.tsx` | 219 | workout title PressStart2P 14 caps | **monoBold 20, drop caps** |

### 4.15 LoginScreen

`mobile/src/screens/LoginScreen.tsx`:

- `MARATHON` brand: **keep PressStart2P 24 accentHi**. Brand is the one place pixel font fully earns its keep.
- `▸ PRESS START`: VT323 18 inkDim — unchanged.
- `EMAIL` / `PASSWORD` field labels (lines 53, 70): PressStart2P 8 → **mono 11 inkDim, mixed-case** → "Email" / "Password".
- `! INVALID LOGIN` error (line 86): PressStart2P 8 → **mono 11 accentDanger, mixed-case** → "! Invalid login".

---

## 5. Density / weight / spacing

The staycation cards have:
- **Bigger title** than VT323 22 — comparable visual weight to ~20pt monoBold.
- **Tighter timestamp** (smaller, dim, sits above the title) — our equivalent is the `WK n · TYPE` line in WhySheet / WorkoutDetailScreen and the type pill on WorkoutCard.
- **Lighter body description** — single line of dim mono.
- **More vertical breathing** between cards (~14px) — Session 2.6 already brought this to 14px on `WorkoutCard` (line 40). Good.

**Specific bumps this pass should make:**

- Page title block on every screen: bottom margin from 16 → **24** (matches staycation header → tabs distance).
- WorkoutCard internal padding: **stays at 12** — the bigger title alone gives the right density.
- StatTile minHeight: 76 → **80** (monoBold value glyph sits a touch taller).
- Sheet titles: bottom margin from 14 → **18**.
- Day-section header (DayCard) bottom margin: 6 → **8**.

**No size shrinks anywhere.** Direction is bigger-where-it-counts (titles), tighter-where-it-doesn't (labels, the new mono 11s replace pixel 8s — same visual height but with x-height + descenders + spacing, they read smaller despite the larger nominal pt).

---

## 6. Tab labels — verdict

**Keep pixel.**

The staycation reference has `SCHEDULE / NOW PLAYING / STATS / SETTINGS` in pixel font with letterspacing in the tab bar. That matches our current `TODAY / WEEK / PROGRAM / CHAT / SETTINGS`. Pixel font here is doing the work it's meant for: tiny, all-caps, identifying tabs at a glance, recurring chrome. **One small bump: 8pt → 9pt** for parity with the reference's slightly-larger tab labels and the resulting tap-target read.

`mobile/src/navigation/RootNavigator.tsx:47-50`:

```ts
tabBarLabelStyle: {
  fontFamily: 'PressStart2P',
  fontSize: 9,            // was 8
  letterSpacing: 1,
},
```

Tab icons (`▣ ▦ ▤ ◇ ⚙`) — keep PressStart2P 14, unchanged.

---

## 7. ASCII mockups

### 7.1 WorkoutCard — before / after

**Before** (PressStart2P doing too many jobs):

```
┌─────────────────────────────────────────────┐
│ █ TEMPO                          [ PLANNED ]│   ← pill 8pt pixel + bracket pixel
│                                             │
│ Tempo  run  —  6mi  @  marathon             │   ← VT323 22, body voice on the title
│ pace                                        │
│                                             │
│ 6 mi   55min   7:30/mi   Z3                 │   ← VT323 16
│                                             │
│ [WHY?] [EDIT]                               │   ← PressStart2P 8 inside 2px borders
└─────────────────────────────────────────────┘
```

**After**:

```
┌─────────────────────────────────────────────┐
│ █ ┃TEMPO┃                        [ PLANNED ]│   ← pill 8pt pixel ON tinted badge bg
│                                             │       (NES-style: filled, rounded)
│ Tempo run — 6mi @ marathon pace             │   ← monoBold 20, crisp title
│                                             │
│ 6 mi · 55min · 7:30/mi · Z3                 │   ← mono 13, dim, tighter
│                                             │
│  Why?    Edit                               │   ← mono 11, soft 1px border, mixed case
└─────────────────────────────────────────────┘
```

The card now has exactly two pixel-font sites (type badge, status pill) — both clearly read as badges. Everything else reads as content.

### 7.2 ProgramScreen header — before / after

**Before**:

```
┌─────────────────────────────────────────────┐
│  P R O G R A M                              │   ← PressStart2P 16, all caps,
│                                             │       feels like an arcade insert-coin
│  marathon-build-2026                        │   ← VT323 16 dim
└─────────────────────────────────────────────┘
```

**After**:

```
┌─────────────────────────────────────────────┐
│  Program                                    │   ← monoBold 20, mixed case,
│                                             │       reads as a section title
│  marathon-build-2026                        │   ← VT323 16 dim (unchanged)
└─────────────────────────────────────────────┘
```

### 7.3 EditQuestSheet — before / after

**Before**:

```
EDIT  QUEST                              ← PressStart2P 14 yellow caps
currently: Easy run                       ← VT323 16 dim

Q U I C K   P I C K                       ← PressStart2P 8
[ EASY  ] [ TEMPO ] [ LONG  ] [INTERVAL]
[ STR-A ] [ STR-B ] [ CROSS ] [ REST   ]  ← chip labels PressStart2P 8

▸ T W E A K  S T A T S                    ← PressStart2P 8 green
D I S T A N C E  ( M I )                  ← PressStart2P 8 dim
[ 6.0           ]                         ← VT323 18

[ Cancel  ]   [ Confirm ]                 ← PressStart2P 10
```

**After**:

```
Edit Quest                                ← monoBold 18 yellow, mixed case
currently: Easy run                       ← VT323 16 dim (unchanged)

Quick pick                                ← mono 11 dim, mixed case
[ EASY  ] [ TEMPO ] [ LONG  ] [INTERVAL]
[ STR-A ] [ STR-B ] [ CROSS ] [ REST   ]  ← chip labels stay pixel 8 (badges)

▸ Tweak stats                             ← mono 11 green
Distance (mi)                             ← mono 11 dim
[ 6.0           ]                         ← VT323 18 (unchanged)

[ Cancel  ]   [ CONFIRM ]                 ← Cancel: monoBold 12 mixed
                                            CONFIRM: pixel 10 caps (primary)
```

The sheet now has a clear hierarchy: monoBold title at the top, mono labels for fields, VT323 for body input, pixel only for badges and the primary action. The chips still read as badges because the pixel font is now contained.

---

## 8. Implementation outline (engineer-facing, tight)

### 8.1 Token edits — `mobile/src/theme/tokens.ts`

Add to the `fonts` const:

```ts
mono: 'JetBrainsMono',
monoBold: 'JetBrainsMonoBold',
```

### 8.2 Asset + load — `mobile/assets/fonts/` + `App.tsx`

- Drop `JetBrainsMono-Regular.ttf` and `JetBrainsMono-Bold.ttf` into `mobile/assets/fonts/`.
- Add the two `useFonts` keys per §3.2.

### 8.3 Primitive component diffs

| File | Change |
|---|---|
| `RetroButton.tsx` | per-tone family/size mapping (§4.2); skip `.toUpperCase()` on non-primary tones |
| `RetroPill.tsx` | unchanged |
| `RetroBorder.tsx` | unchanged (Feature A may touch radius) |

### 8.4 Component diffs

In order — small, focused PRs possible per row:

1. `WorkoutCard.tsx` — title to monoBold 20, type to RetroPill badge, metas to mono 13, mini-buttons to mono 11
2. `WhySheet.tsx` — markdown styles + 4 label sites + title swap
3. `WorkoutDetailScreen.tsx` — markdown styles + header CTAs + comparison table column heads + section labels
4. `EditQuestSheet.tsx` — 6 label swaps; keep chip labels pixel
5. `ProposalSheet.tsx` — 4 label swaps; option label to monoBold
6. `DisplacedSheet.tsx` — 2 swaps; keep day chips pixel
7. `DayCard.tsx` + `DraggableWeekList.tsx` — day name to mono 12 mixed, REST to mono 11
8. `StatTile.tsx` — label to mono 11, value to monoBold 22
9. Screens (`TodayScreen`, `ProgramScreen`, `SettingsScreen`, `WeekScreen`, `LoginScreen`) — page titles + chrome labels
10. `RootNavigator.tsx` — tab font size 8 → 9

### 8.5 What we explicitly do NOT touch in this pass

- Color palette (Feature A territory)
- Spacing tokens (Feature B territory)
- Section header pattern (already correct from Session 2.6)
- VT323 body voice (it's the right voice for terminal-style copy)
- WeekTile / RaceMilestoneTile / CycleLane chrome (cycle lane is its own visual language)
- Status pill bracket convention (`[ PLANNED ]`) — matrix nod stays
- The press-translate animation on primary buttons

---

## 9. Done criteria (engineer self-check)

An engineer is done when:

1. **No PressStart2P font usage at sizes < 10pt anywhere except** RetroPill (8pt is a deliberate badge size) and the cycle-lane chrome (WeekTile 8pt label is the badge of the lane).
2. **Card titles, page titles, sheet titles, comparison-table heads** all render in `JetBrainsMono-Bold` at 16–22pt depending on hierarchy.
3. **Chrome labels** (LAST SYNC, DISTANCE, WK n · TYPE, etc.) all render in `JetBrainsMono` 11pt mixed-case (most should drop `.toUpperCase()` — visual cue is the dim color, not the caps).
4. **Tab labels** are PressStart2P 9 (up from 8).
5. **Badges** (type pills, family pills, status brackets, day-of-week chips, quick-pick chips, NES-style platform-equivalent badges) **stay pixel font**.
6. **Brand title** (`MARATHON`) and **race milestone** (`⚑ NYC MARATHON`) **stay pixel**.
7. Side-by-side with `staycation-exe.jpg`, the typographic hierarchy reads the same: bold square mono titles, dim mono labels, pixel only for badges and the brand.
8. App still launches; `useFonts` resolves; no `Text` components fall through to system font (would show as visibly different rendering on iOS vs Android).
9. `mobile/src/theme/tokens.ts` `fonts` exports `mono` and `monoBold` and they're used by name (no inline `'JetBrainsMono'` strings except in `App.tsx` registration).
10. Visual smoke pass on Today / Week / Program / Settings / WorkoutDetail / all four sheets / Login. Each screen has at most ~3 pixel-font sites; everything else is mono or VT323.

---

## 10. Open questions

1. **Should `SectionHeader.tsx` move from VT323 to mono?** — Currently it's VT323 18 cyan, set in Session 2.6. The staycation reference's `▸ Day Session` looks closer to a clean mono than VT323's CRT-style. This doc leaves SectionHeader untouched (Feature C may revisit), but a single follow-up flip from `fontFamily: 'VT323'` → `fontFamily: 'JetBrainsMono', fontSize: 14` would push the cyan headers from "terminal" to "polished retro." Worth a one-line A/B from the implementer.
2. **Token name — `mono` / `monoBold` or `body` / `bodyBold`?** — I went with `mono` to make it semantically clear what it *is* (not "body" — VT323 is also body). If the team prefers role names over typeface names, rename now before adoption.
3. **Drop `.toUpperCase()` on quick-pick chips** (`EASY`, `LONG`, …)? — Reference uses caps for badges (NES, SNES). Our quick-pick chips are also badges in spirit. This doc keeps caps on them. If chips read as buttons more than badges in QA, flip them.
4. **VT323 retirement — when?** — VT323 is still earning its keep on workout titles (now being moved to monoBold), markdown body, sub-labels, stat values. Net usage drops by ~30% with this pass. If the team wants to consolidate to one mono in a later pass, JetBrains Mono Regular at 16pt could replace VT323 16 across the board. Not recommended for this pass — VT323 still gives the descriptions and stat values their CRT/screen feel.
