# Session 2.8 — Staycation IA + Visual Overhaul Design

**Status:** design (no code)
**Date:** 2026-05-07
**Owner:** session lead (CBell)
**Branch target:** `session-2/backend-move-endpoints` (doc-only; implementation in a follow-up)
**Reference image:** `docs/superpowers/specs/refs/staycation-exe.jpg` (also `Example_Screen_Grab_2.jpg` in repo root — same view, slightly different crop)
**Note:** This supersedes the typography sweep from Session 2.7's Feat D in spirit — that pass got the fonts right but didn't touch IA or card composition. This pass touches both.

---

## 1. Brief

User feedback after Session 2.7 demo:

> "The UX and styling of the UIs is….woof. Needs some work. Lets use that theme!"

Where "that theme" = `staycation.exe`'s schedule view. Session 2.6/2.7 nailed the palette + typography but the *information architecture* and *card composition* didn't follow through. This spec closes that gap.

**Goal:** Every content screen reads like a sibling of the staycation reference: pixel-green brand banner, mono caret subhead, list of clean rounded-bordered cards with `meta + small filled badge → monoBold title → lighter mono description → chevron`. No inline buttons on cards, no visual chrome stacking, generous breathing room.

**Anti-goal:** Don't tear up the data model, the API, or the navigation tree. This is purely a presentation-layer rework.

---

## 2. What the reference is doing — explicit pattern audit

Per the screenshots:

### 2.1 Banner (top of every content screen)

- Wordmark: `STAYCATION.EXE` in PressStart2P, ~24-28pt, color phosphor green (`#22d36a`-ish).
- Trailing dot in the wordmark is itself a visual accent — a green pixel-square. (We can mirror with a punctuation glyph or a small block.)
- Top right: `v1.0 ◦` — small mono dim version + a tiny circle indicator (status / connection).
- Subhead caret line directly under the brand: `▸ RETRO_GAMING_TRACKER — 0/22 CLEARED` in mono dim caps. Communicates the screen's status / mode.
- 1px slate horizontal rule directly under the subhead, full width.

**Marathon analog:**

```
MARATHON                                   v1.0 ◦
▸ MARATHON_TRILOGY — WK 4 / 28 · MCM 173d
─────────────────────────────────────────────────
```

Subhead text is screen-aware:
- Today: `▸ MARATHON_TRILOGY — WK 4 / 28 · MCM 173d`
- Week: `▸ MAY 4 – MAY 10 — WK 4 / 28`
- Program: `▸ MARATHON_TRILOGY — 3 PHASES · 364 SESSIONS`
- WorkoutDetail: `▸ WK 4 · TUESDAY · 5/6/2026`
- Settings: `▸ ATHLETE — runner@marathon.dev`

### 2.2 Tabs (horizontal nav row in reference; bottom-tab on mobile)

Reference: top-of-content row with 4 tabs. Active = solid filled rounded-corner pill (phosphor green fill, white pixel text + glyph icon). Inactive = no background, mono cyan-dim icon + label.

**Marathon analog:** keep bottom tab bar (mobile UX). Apply the same active-pill treatment: active tab gets a green-filled rounded pill *behind* the icon + label; inactive stays icon + label only with `colors.inkDim`. We currently use a single tint color on active — needs the pill background.

### 2.3 Day toggle (segmented control)

Reference shows a two-button toggle: `THURSDAY` (active green fill, white pixel text) | `FRIDAY` (transparent, cream text). Forms one rounded-corner pill — left half green, right half transparent, joined by a single border.

**Marathon analog:** depends on screen.
- **Today:** `TODAY | TOMORROW` segmented pill — peek tomorrow without leaving.
- **Week:** could replace the prev/next chevrons with a 7-segment day toggle showing `MON TUE WED THU FRI SAT SUN`. Today highlighted phosphor green; tap any day to scroll-anchor.

### 2.4 Section header (`▸ Day Session`)

Cyan mixed-case mono, ~16-18pt, with `▸` caret. We already have `SectionHeader` for this.

**Marathon analog:** use `SectionHeader` everywhere we currently have `<Text>` headers. Audit and replace.

### 2.5 Cards — the keystone

Each card is:

- **Single-line top row:** time range (`9:30-10:00`) in mono cream/dim, left-aligned. Followed by a small filled badge (`NES` red bg / `SNES` purple bg) right next to it. Both inline.
- **Title row:** monospace bold (Geist Mono Bold or similar) ~18pt, full width, e.g. `Super Mario Bros. 3`.
- **Sub row:** lighter mono (looks like Geist Mono regular), italic-leaning, smaller (~14pt), description e.g. `Warm-up — classic Nintendo joy. Worlds 1-2.`
- **Right edge:** subtle `>` chevron in cyan/mint, vertically centered, indicating tappable.
- **Container:** 1px slate border (~`#2a3045`), rounded ~6-8px corners, NO offset shadow, generous padding (~14px vertical, ~18px horizontal), ~10-12px gap between cards.

**Critical: NO inline action buttons.** Cards are pure tap targets. All actions (edit, why, mark-done, skip) live in the *detail view* the card navigates to.

---

## 3. Current-state gap audit

Anchored in actual files:

### 3.1 `WorkoutCard.tsx`

Current composition (lines 39-122):
- `<RetroBorder>` wrapper ✓ (correct visual treatment after 2.7)
- Top row: family-tinted **dot** (10×10 colored square) + type label (`EASY`) + status pill (`[ PLANNED ]`) — **wrong shape**. Reference uses meta + filled badge.
- Title in `monoBold` 18 ✓ (right after typography sweep)
- Optional `↻ was:` line ✓ (matches "card sub" voice)
- Meta line: distance + duration + pace + HR all on one line — **acceptable but reference has only ONE descriptive sub line, not 4 inline metrics**.
- **Inline `Why?` and `Edit` buttons** — *fundamentally wrong* per the reference. Cards are tap-only.
- No right-edge chevron — **missing** the affordance the reference uses.

**Verdict:** rework the entire composition. The visual treatment (border, font, spacing) is right; the *structure* is wrong.

### 3.2 `TodayScreen.tsx`

Current header: VT323 date string + monoBold "What's on tap" + cycle-progress sub + SYNC pill stacked below. Then coach brief panel, workouts, recent runs strip.

**Gap:** no brand banner. The "What's on tap" title is pure UI copy, not branded. SYNC pill placement is fine as a corner action.

### 3.3 `WeekScreen.tsx`

Header: chevrons + week range + WK X/Y + "▸ JUMP TO TODAY". No brand. Day cards rendered via `DraggableWeekList`.

**Gap:** no brand banner. The chevron + week-range pattern is fine but could be reskinned as a 7-day segmented toggle for staycation feel.

### 3.4 `ProgramScreen.tsx`

Header: pixel `PROGRAM` + plan name in VT323 sub. Three-column lane layout (P1/P2/P3) with WeekTiles. WeeklyMileageTracker below.

**Gap:** the 3-column layout is information-dense but doesn't read like staycation's vertical card list. Either:
- (a) Keep 3 columns but replace WeekTiles with mini staycation-style cards (badge + title + sub).
- (b) Refactor to a single-column scrolling list with `▸ Phase 1 — MCM` section headers, each followed by a list of week cards.

Recommendation: (a). The trilogy framing is the whole point of the world-map view; flattening it loses the narrative. We just need to restyle the WeekTiles inside the lanes to match staycation card composition (compressed for the narrow column width).

### 3.5 `WorkoutDetailScreen.tsx`

Already in good shape after 2.7. Uses SectionHeader for sub-sections. Just needs the brand banner.

### 3.6 `SettingsScreen.tsx`

Already cards-in-list. Just needs the brand banner. Optional: convert each row in the Plan / Garmin cards to mini-staycation cards (action items as cards instead of inline buttons).

### 3.7 `LoginScreen.tsx`

Currently the only screen with a strong brand presence. Already pixel `MARATHON` + caret subhead. Effectively the staycation pattern landing page. Keep as-is.

### 3.8 Tab bar (`RootNavigator.tsx`)

Active tab uses `tabBarActiveTintColor: colors.accentRun`. No background fill on the active state. Reference uses a filled rounded-corner pill behind the icon+label.

### 3.9 `WhySheet.tsx`

The WHY? button on the card opens this sheet. Reference doesn't have a "why" affordance at all — cards just navigate to detail, where the full prescription + intent live. **Recommendation:** delete WhySheet. Move its content into WorkoutDetail (which already shows description_md + intent_md). One less surface to maintain.

---

## 4. Information architecture changes per screen

### 4.1 `LoginScreen` — no IA change

Already on-brand. Visual tweaks only if anything looks off relative to the new card style guide.

### 4.2 `TodayScreen` — restructure

Current order: VT323 date / "What's on tap" title / cycle progress / SYNC pill / coach brief / workouts / recent runs.

**New order:**

```
+------------------------------------------------+
| MARATHON                            v1.0 ◦     |    ← BrandBanner
| ▸ MARATHON_TRILOGY — WK 4 / 28 · MCM 173d      |
| ─────────────────────────────────────────────  |
|                                                |
| [ TODAY ]   [ TOMORROW ]                  ↻    |    ← DayToggle + SYNC icon
|                                                |
| ▸ Today's session                              |    ← SectionHeader
| +-------------------------------------------+  |
| | TUE 5/6   [RUN]                        >  |  |    ← StaycationCard (workout)
| | Easy run · 5mi                            |  |
| | Conversational pace, recovery focus.      |  |
| +-------------------------------------------+  |
|                                                |
| ▸ Coach brief                                  |    (only if non-null)
| Tempo day — 6mi at 11:00/mi target. ...        |
|                                                |
| ▸ Recent runs                                  |
| [horizontal scroll of mini run cards]          |
+------------------------------------------------+
```

**Changes:**
- Replace VT323 date + "What's on tap" with `BrandBanner`.
- Add `DayToggle` (`TODAY` | `TOMORROW`) — when set to TOMORROW, swaps the `▸ Today's session` header to `▸ Tomorrow's session` and the workout list to tomorrow's planned. Both branches use the same existing `usePlanWeek` data — no new endpoint.
- Move SYNC pill to the right edge of the day-toggle row (small `↻` icon button instead of a labeled SYNC pill — saves space).
- Coach brief stays but as a `▸ Coach brief` SectionHeader + plain-mono paragraph, NOT inside a bordered card. Lighter weight visual.
- Workout cards adopt new staycation composition (see §5.2 below).

### 4.3 `WeekScreen` — restructure

```
+------------------------------------------------+
| MARATHON                            v1.0 ◦     |
| ▸ MAY 4 – MAY 10 — WK 4 / 28                   |
| ─────────────────────────────────────────────  |
|                                                |
| [‹] [MON][TUE][WED][THU][FRI][SAT][SUN] [›]    |    ← 7-day toggle row
|                                                |
| ▸ Mon 5/4                                      |
| +-------------------------------------------+  |
| | EASY · 5MI [RUN]                       >  |  |
| | Easy run                                  |  |
| | Conversational pace, recovery focus.      |  |
| +-------------------------------------------+  |
|                                                |
| ▸ Tue 5/5                                      |
| +-------------------------------------------+  |
| | TEMPO · 6MI [RUN]                      >  |  |
| | Tempo run                                 |  |
| | Threshold work, controlled effort.        |  |
| +-------------------------------------------+  |
|                                                |
| ... (Wed-Sun)                                  |
+------------------------------------------------+
```

**Changes:**
- BrandBanner replaces existing chevron-and-range header.
- Prev-/next-week chevrons move to flank the 7-day toggle (`‹ MON TUE WED THU FRI SAT SUN ›`).
- The 7-day toggle scrolls the list to that day's section (smooth scroll). Today highlighted phosphor-green.
- Each day rendered as: `▸ Mon 5/4` SectionHeader + 0..N StaycationCards beneath.
- Drag-to-move continues to work — wrap each StaycationCard in the existing Reanimated draggable wrapper.

### 4.4 `ProgramScreen` — restructure

Keep three-column lane layout. Restyle WeekTiles inside lanes to match staycation card composition (compressed).

```
+------------------------------------------------+
| MARATHON                            v1.0 ◦     |
| ▸ MARATHON_TRILOGY — 3 PHASES · 364 SESSIONS   |
| ─────────────────────────────────────────────  |
|                                                |
| [ ON-PLAN 92% ] [ CYCLE 42mi ] [ STREAK 11d ]  |    ← compressed StatTile row
| [ NEXT MILESTONE ] [ PROGRESS ]                |
|                                                |
| ▸ The trilogy                                  |
| +----------+ +----------+ +----------+         |
| | P1 MCM   | | P2 DISN  | | P3 DELAW |         |    ← 3 cycle lanes
| | 28 weeks | | 11 weeks | | 13 weeks |         |
| | +------+ | | +------+ | | +------+ |         |
| | |WK 1  | | | |WK 1  | | | |WK 1  | |         |    ← compact StaycationCard
| | |✓ 18mi| | | |  *   | | | |  *   | |         |       (badge + title + meta)
| | +------+ | | +------+ | | +------+ |         |
| | ...      | | ...      | | ...      |         |
| | [⚑ MCM]  | | [⚑ DISN] | | [⚑ DELW] |         |
| +----------+ +----------+ +----------+         |
|                                                |
| ▸ Weekly mileage — P1 MCM                      |
| [bar chart with cumulative overlay]            |
+------------------------------------------------+
```

**Changes:**
- BrandBanner.
- StatsPanel rendered as a compressed inline row of pill-shaped tiles (instead of large RetroCards). Saves vertical real estate.
- `▸ The trilogy` SectionHeader before the 3 lanes.
- WeekTile composition rework (see §5.3).
- WeeklyMileageTracker stays as-is structurally, just the surrounding header gets the SectionHeader treatment.

### 4.5 `WorkoutDetailScreen` — light restructure

```
+------------------------------------------------+
| MARATHON                            v1.0 ◦     |
| ▸ WK 4 · TUE · 5/6/2026                        |
| ─────────────────────────────────────────────  |
|                                                |
| [ ‹ Back ]                          [ EDIT ]   |    ← header chip row
|                                                |
| EASY RUN [RUN]                                 |    ← pixel type pill + family badge
| Easy run · 5mi                                 |    ← monoBold 22 title
|                                                |
| ▸ Prescription                                 |
| <markdown>                                     |
|                                                |
| ▸ Intent                                       |
| <markdown>                                     |
|                                                |
| ▸ Planned vs actual    (only if completed)     |
| <stat panel>                                   |
|                                                |
| ▸ Reconciliation                               |
| <stat block in RetroCard>                      |
|                                                |
+------------------------------------------------+
| [ MARK DONE ]   [ SKIP WORKOUT ]               |    ← bottom action bar
+------------------------------------------------+
```

**Changes:**
- BrandBanner replaces "BACK" header bar.
- Back + Edit move to a thin secondary header chip row directly under the banner.
- Title block gets a clearer pixel-pill type badge + family badge (matching card composition).
- Bottom action bar with two buttons (MARK DONE primary + SKIP danger). Replaces the current single button stacked layout.

### 4.6 `SettingsScreen` — light restructure

- BrandBanner with subhead `▸ ATHLETE — runner@marathon.dev`.
- Sections (`▸ Plan`, `▸ Garmin`, `▸ Account`) already use SectionHeader after 2.7.
- Reset start date + Sign out become bottom-stacked action buttons rather than mid-list.

### 4.7 `LoginScreen` — no change

Already on-brand. Validate visually after the StaycationCard / button-tone restyle but expect zero-or-near-zero edits.

---

## 5. New components

### 5.1 `BrandBanner` — new

**File:** `mobile/src/components/BrandBanner.tsx`

```tsx
interface Props {
  subhead: string;        // e.g. "MARATHON_TRILOGY — WK 4 / 28 · MCM 173d"
  meta?: string;          // top-right chip, default "v1.0 ◦"
}
```

Render:
- Outer `View` with `paddingHorizontal: 20, paddingTop: 12, paddingBottom: 16`
- Top row (flex-row, justify-between):
  - `MARATHON` — `fonts.pixel`, fontSize 24, color `colors.accentRun`, letterSpacing 2 (the green wordmark)
  - `meta` — `fonts.mono`, fontSize 11, color `colors.inkDim`, with a small `◦` glyph
- Subhead row, beneath:
  - `▸ {subhead}` — `fonts.mono`, fontSize 12, color `colors.inkDim`, letterSpacing 0.5, marginTop 4
- Bottom: 1px line `colors.line`, marginTop 12

Used on every content screen.

### 5.2 `WorkoutCard` — rewritten

**File:** `mobile/src/components/WorkoutCard.tsx` (overwrite)

New props (simpler):
```tsx
interface Props {
  workout: PlannedWorkoutOut;
  onPress?: () => void;
  /** when true, the card renders compact for narrow contexts (Program tab cycle lanes) */
  dense?: boolean;
}
```

Drop `onWhy`, `onEdit`, `compact`. WhySheet is removed (§7); EDIT lives in WorkoutDetail.

Composition:
```
┌────────────────────────────────────────────────────┐
│ {meta}    {familyBadge}   {statusBadge?}        >  │
│ {title}                                            │
│ {sub}                                              │
└────────────────────────────────────────────────────┘
```

Where:
- **meta** = `dayName().toUpperCase() + ' ' + M/D` (e.g., `TUE 5/6`). For dense mode: `WK4 · TUE`.
- **familyBadge** = `RetroPill variant="badge"` with family-mapped color:
  - `running` → bg `colors.accentRun`, text `colors.bg`, label `RUN`
  - `strength` → bg `colors.accentStrength`, text `colors.ink`, label `STR`
  - `other` → bg `colors.accentBadgePurple`, text `colors.ink`, label `CROSS` or `REST`
- **statusBadge** = only shown if status ≠ planned:
  - `done` → outlined green `[ DONE ]`
  - `skipped` → filled red `SKIP`
  - `moved` → outlined cyan `[ MOVED ]`
- **chevron** = `>` glyph in `colors.accentCyan`, fontSize 18, on right edge
- **title** = `${workout.title}` (and append distance if running: `${workout.title} · ${distance_mi}mi`); `fonts.monoBold` 18, color `colors.ink`, line-height 24
- **sub** = first sentence of `workout.intent_md` (split on `.` and `!`, take first chunk, trim, max 90 chars). `fonts.mono`, 14, color `colors.inkDim`, line-height 20
- If `original_snapshot` present: prepend a small `↻ was: {snapshot.title}` row above the meta — keeps the displaced-original audit signal

Container styling unchanged (`RetroBorder`, soft slate, no shadow), padding `paddingHorizontal: 14, paddingVertical: 12`.

`dense` mode:
- Same composition, but `padding: 8`, title fontSize 13, sub line-clamp 1, meta fontSize 10. Used inside `ProgramScreen` cycle lanes.

### 5.3 `WeekTile` — drop, replaced by dense `WorkoutCard`

Or, since WeekTile aggregates a whole week (not a single workout), keep it but restyle. Actually a WeekTile shows aggregate week info (WK N · status · mileage glyph), which is a different shape than a workout card. **Keep WeekTile** but adopt the same visual primitives:
- Border + radius + no shadow ✓ (already done)
- Inline filled-rounded badge for status (`DONE` / `NOW` / `PEAK` / `RACE`) instead of bracketed pixel pill
- monoBold title row with `WK 04` + mileage glyph in mono sub

### 5.4 `DayToggle` — new

**File:** `mobile/src/components/DayToggle.tsx`

Two-segment pill for `TODAY | TOMORROW` on Today screen, or n-segment for `MON…SUN` on Week screen.

```tsx
interface Props<T extends string> {
  options: readonly T[];        // ['TODAY', 'TOMORROW'] or ['MON','TUE',...]
  value: T;
  onChange: (v: T) => void;
  highlight?: T;                // optional "today" highlight (different from selected)
}
```

Render:
- Outer pill: `borderWidth: 1, borderColor: colors.line, borderRadius: radius.lg`, flex-row of segments
- Each segment:
  - Equal flex
  - Active: `backgroundColor: colors.accentRun`, text `colors.bg`, fontFamily `fonts.pixel`, fontSize 10
  - Inactive: transparent, text `colors.ink`, fontFamily `fonts.mono`, fontSize 12
  - Highlight (the "today" of the week, if not selected): text in `colors.accentRun` instead of `colors.ink`
- Internal dividers: 1px `colors.line` between segments

### 5.5 Tab bar restyle (active = filled pill)

**File:** `mobile/src/navigation/RootNavigator.tsx`

Change `tabBarActiveBackgroundColor` and customize `tabBarItemStyle` to give the active tab a filled rounded-corner pill backdrop. Inactive tabs render as before but with no background.

Pseudocode:
```tsx
screenOptions={({ route, navigation }) => ({
  tabBarStyle: { /* unchanged */ },
  tabBarLabelStyle: { /* unchanged */ },
  tabBarItemStyle: ({ /* per-tab dynamic */ }),
})}
```

Since react-navigation's `tabBarItemStyle` is static, do a custom `tabBarButton` wrapper that paints the green pill behind the icon+label when focused.

```tsx
function PillTabBarButton({ children, accessibilityState, ...rest }: BottomTabBarButtonProps) {
  const focused = accessibilityState?.selected === true;
  return (
    <Pressable
      {...rest}
      style={{
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 6,
      }}
    >
      <View style={{
        backgroundColor: focused ? colors.accentRun : 'transparent',
        paddingHorizontal: 14,
        paddingVertical: 6,
        borderRadius: radius.lg,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
      }}>
        {children}
      </View>
    </Pressable>
  );
}
```

Apply via `screenOptions={{ tabBarButton: PillTabBarButton }}`.

When focused, also override the icon + label colors to `colors.bg` (so they read on green). Inactive uses `colors.inkDim`.

### 5.6 New: top-of-screen `▸ caret` for status

Already covered by `BrandBanner.subhead` and `SectionHeader`. No new component.

### 5.7 New: secondary action bar (`BottomActionBar`)

**File:** `mobile/src/components/BottomActionBar.tsx`

For WorkoutDetail's MARK DONE / SKIP row, plus other screens that need fixed-bottom action bars.

```tsx
interface Props {
  children: React.ReactNode;     // RetroButton or similar
}
```

Renders:
- Fixed-position container at bottom of screen
- 1px top border `colors.line`
- backgroundColor: `colors.bgPanel`
- padding: `paddingHorizontal: 16, paddingVertical: 12`
- safe-area aware (uses `useSafeAreaInsets`)
- Children laid flex-row with even spacing (`gap: 12`)

---

## 6. Removals

### 6.1 `WhySheet.tsx` — DELETE

Reference cards have no inline "why" affordance. Detail navigation handles it. Saving:
- One file, ~80 lines
- The corresponding `whyWorkout` state in TodayScreen, WeekScreen
- The `onWhy` prop on WorkoutCard
- The corresponding mileage/why click logic

Move forward: tap a card → WorkoutDetail. Description + intent are already there.

### 6.2 Inline `Why?` and `Edit` buttons on cards — DELETE

Same rationale. EDIT button moves to WorkoutDetail's secondary header (already exists there).

### 6.3 `compact` prop on WorkoutCard — REPLACE with `dense`

Functional rename: `dense` is what the Program tab needs (smaller padding, smaller font, single-line sub). Existing call sites (DayCard, DraggableWeekList) currently pass `compact` — they should NOT pass dense (full size on Today/Week). The Program tab's lane will pass `dense`.

---

## 7. Color + typography (already in place)

No new tokens. Tokens established in 2.6/2.7 cover everything:

| Token | Hex | Use |
|---|---|---|
| `colors.bg` | `#0e1320` | Page background |
| `colors.bgPanel` | `#1a1f33` | Card / panel background, BrandBanner backdrop |
| `colors.bgPanelAlt` | `#222a44` | Nested panels (e.g. inside RetroBorder) |
| `colors.ink` | `#e8e8d8` | Primary text |
| `colors.inkDim` | `#8b9bb3` | Subhead text, dim labels |
| `colors.inkMute` | `#5a6478` | Placeholder, very-dim |
| `colors.line` | `#2a3045` | All borders, horizontal rules |
| `colors.accentRun` | `#22d36a` | Brand wordmark, primary CTAs, active tab pill, day-toggle active, family=running badge |
| `colors.accentCyan` | `#7ec8c8` | SectionHeader caret + text, chevrons |
| `colors.accentStrength` | `#e8593a` | family=strength badge |
| `colors.accentBadgePurple` | `#7c5cd8` | family=cross / SNES-style badges |
| `colors.accentDanger` | `#e84a4a` | skipped / destructive CTAs |
| `colors.accentHi` | `#f7d51d` | current-week / peak markers |
| `fonts.pixel` | `PressStart2P` | Brand wordmark, tab pill labels, badge labels |
| `fonts.mono` | `JetBrainsMono` | Body labels, chips, meta lines |
| `fonts.monoBold` | `JetBrainsMono-Bold` | Card titles, section/page titles |
| `fonts.body` | `VT323` | Long-form prose (markdown body, descriptions) |

---

## 8. Phasing

Single sprint, ~½ day of focused work. Phasing organized to commit at each major milestone for easy revert.

### Phase A — Foundation components (no screen changes yet)

1. `BrandBanner` component
2. `DayToggle` component
3. `BottomActionBar` component
4. Tab bar restyle in RootNavigator (active = filled green pill)

After this phase: existing screens look unchanged because nothing consumes the new components yet, except the tab bar (which restyles immediately).

### Phase B — `WorkoutCard` rework

5. Rewrite `WorkoutCard.tsx` per §5.2. Update existing call sites (TodayScreen, DayCard, DraggableWeekList) to drop `onWhy`/`onEdit` and stop passing them. Add `dense` prop.

After this phase: Today, Week, and Program WorkoutCards adopt the staycation composition. Drag-to-move still works.

### Phase C — Screen IA restructure

6. `TodayScreen` — adopt BrandBanner + DayToggle + remove WhySheet ref + restructure section headers
7. `WeekScreen` — adopt BrandBanner + 7-day DayToggle + restructure as `▸ {Day}` SectionHeader-grouped list
8. `WorkoutDetailScreen` — adopt BrandBanner + BottomActionBar
9. `ProgramScreen` — adopt BrandBanner + restyle StatsPanel as compressed pill row + WeekTile dense restyle
10. `SettingsScreen` — adopt BrandBanner

### Phase D — Removals + cleanup

11. Delete `WhySheet.tsx`. Remove all imports + state + render references in TodayScreen, WeekScreen.
12. Delete the `_clear_recent_completed_cache` references on the deleted `useWhy` flow if any (check during implementation).
13. Update `mobile/src/api/types.ts` — no shape change needed.
14. Final mobile typecheck.

### Phase E — QA + close-out

15. Manual smoke on every screen at the demo URL.
16. Update `PROJECT_TRACKER.md` + `MEMORY.md`.

**Total:** ~12-15 commits.

---

## 9. Out of scope (deferred)

- **Animations.** Active-tab pill could animate on focus change (slide/scale). Defer.
- **Pull-to-refresh shimmer.** Currently a basic `RefreshControl`. Custom retro-styled one is nice-to-have, not in this pass.
- **Card hover/press state.** A subtle `Pressable` ripple/dim on press. Worth adding if it's free; skip if it adds complexity.
- **Haptics on tab change.** `expo-haptics` already in deps; could add a light tick on tab switch. Defer.
- **Status icon in BrandBanner top-right.** The `◦` glyph is a placeholder; making it dynamic (e.g., online/offline indicator, sync-state) is a future feature.
- **Coach brief presentation.** Currently inside a RetroBorder. This pass moves it to a SectionHeader + plain-mono paragraph (lighter weight). Heavier brief styling (e.g., a callout box with a coach avatar) — defer.

---

## 10. Done criteria

A future implementation session can call this overhaul complete when:

**Visual**
- [ ] BrandBanner appears at the top of Today, Week, Program, WorkoutDetail, Settings
- [ ] Active bottom tab renders as a filled phosphor-green rounded pill
- [ ] Today screen has a `TODAY | TOMORROW` segmented pill that swaps the workout list
- [ ] Week screen has a 7-day segmented row that scroll-anchors to that day's section
- [ ] WorkoutCard renders the staycation composition (meta + family badge + monoBold title + mono sub + chevron) on every screen that uses it
- [ ] No card has inline Why?/Edit buttons anywhere
- [ ] Status (done/skipped/moved) shows as a small badge in the card, not a bracketed pill
- [ ] WorkoutDetail's BACK + EDIT live in a thin chip row under the banner; MARK DONE + SKIP live in a fixed BottomActionBar
- [ ] Program tab's WeekTiles use dense card composition matching staycation
- [ ] Coach brief renders as a `▸ Coach brief` SectionHeader + plain paragraph (no nested RetroBorder)

**Functional**
- [ ] Drag-to-move on Week screen still works after card rework
- [ ] All existing flows (edit, mark done, skip, move, reschedule) still work; entry points moved to WorkoutDetail
- [ ] Day-toggle on Today shifts the workout list to tomorrow's plan without errors
- [ ] 7-day toggle on Week scrolls to the right section
- [ ] Tab bar focus state updates correctly on navigation

**Code**
- [ ] `WhySheet.tsx` deleted; no stale imports remain
- [ ] Mobile typecheck clean (`tsc --noEmit`)
- [ ] No new dependencies added
- [ ] Commit count ~12-15, each one revertable in isolation

---

## 11. Risk register

1. **Active-tab pill may visually conflict with bottom tab bar height.** The pill expands the tab item slightly. Test on both iPhone and web; if it bleeds outside the bar, reduce the pill's vertical padding from 6→3.
2. **Removing WhySheet might confuse existing muscle memory.** WHY? was a quick-peek for intent. Mitigation: ensure the first paragraph of intent is the first thing visible on WorkoutDetail under "▸ Intent" — same data, one extra tap.
3. **7-day toggle on narrow phones may not fit Mon-Sun horizontally.** Each day is ~3 letters; on a 320px screen with chevrons that's tight. Mitigation: use first-letter fallback (`M T W T F S S`) on viewport <360px.
4. **`dense` mode on Program tab cycle lanes might still look cramped.** The lanes are very narrow (33% of screen each). If the dense composition feels wrong, fall back to a simpler 2-line layout: WK# + status badge on row 1, mileage glyph on row 2 — drop the description line for dense mode entirely.
5. **WorkoutDetail BottomActionBar conflicts with safe-area on iPhone X+.** Use `useSafeAreaInsets()` and add bottom padding so the bar doesn't hug the home-indicator.

---

## 12. Reference image checklist

For visual fidelity, before declaring this overhaul done, place a screenshot of the marathon-app Today screen next to `docs/superpowers/specs/refs/staycation-exe.jpg` and verify:

- [ ] Brand wordmark same weight + color
- [ ] Subhead caret + dim mono caps style same
- [ ] Section header `▸ ` cyan mixed-case same
- [ ] Card border weight + corner radius same
- [ ] Card padding + spacing rhythm same
- [ ] Badge filled-rounded shape same
- [ ] Right chevron present and cyan
- [ ] Tab bar active pill present and phosphor green

If any of those visual matches fail, iterate before merging.

---

## Appendix — Open questions for the user

1. **DayToggle on Today — `TODAY | TOMORROW` or different?** Could also be `YESTERDAY | TODAY | TOMORROW` (3-segment), or omitted entirely (single-day view, use Week tab for navigation). **Recommend: 2-segment `TODAY | TOMORROW`** — peeks the next day without changing tab.
2. **Subhead text per screen — sign off on the wording above (§4.x)?** Easy to tweak.
3. **`v1.0 ◦` top-right of banner — keep, or drop?** Recommend keep; lightweight UX flair that mirrors the staycation reference. Status `◦` can be a simple dim glyph for v1; live status indicator (online/sync) is a v2 feature.
4. **WeekTile dense composition tradeoff (risk #4 above) — are you OK with potentially dropping the description line in dense mode if cramped?** Recommend yes.
5. **WhySheet deletion — comfortable losing the long-press peek?** WhySheet currently opens on tap of `Why?` button on cards. Removal puts the same content one tap further (card → detail → already there). Recommend yes.
