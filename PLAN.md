# Marathon Trilogy Training Plan v3.2

> This file is **structured data**. Claude Code reads it during seeding to
> populate `planned_workouts`. Keep the format consistent — the seed script
> parses the workout tables.

## Athlete Profile

```yaml
name: "[FILL IN]"
email: "[FILL IN]"
hr_zones:
  z1: [0, 130]      # recovery
  z2: [131, 145]    # easy aerobic — most training lives here
  z3: [146, 160]    # steady moderate (sparingly)
  z4: [161, 172]    # tempo / threshold
  z5: [173, 999]    # intervals only
pace_targets:
  easy: "12:00-13:30"      # conversational
  marathon_pace: "11:10-11:25"
  tempo: "controlled but stronger than MP"
  long_run: "12:30-13:30"
injury_notes_md: |
  History of IT band / lateral knee pain past mile 14, surfaced in MCM 2023.
  Prehab focus: glute med, hip stability, cadence.
  Rule: any knee pain in weeks 17-19 of Phase 1 → cap peak long run (W20) at 20mi.
```

## The Three Races

| Cycle | Race | Date | Goal |
|---|---|---|---|
| 1 | Marine Corps Marathon | 2026-10-25 (Sun) | Sub-5:00, finish healthy, peak confidence run |
| 2 | Walt Disney World Marathon | 2027-01-10 (Sun) | Sub-5:00, party marathon, enjoy |
| 3 | Coastal Delaware Marathon | 2027-04-11 (Sun) | Sub-5:00, finish the trilogy healthy |

**All three goals: sub-5:00 (~11:15/mile), healthy, enjoyed.**

## Plan Philosophy (loaded into `plans.philosophy_md`)

```markdown
1. **Durability over peak fitness** — finishing three marathons healthy beats
   peaking for one.
2. **Flexibility is structural** — fixed lunch lifts Mon/Fri, a flexible trail
   block Tue/Wed/Thu, a weekend slider. The runs that matter are the long run
   and the one quality run; everything else flexes around real life.
3. **Knee protection first** — strength work and specific glute med / hip
   stability prehab protect the knee that flared past mile 14 last cycle.
4. **Confidence on MCM only** — 21-22 mi peak long run for cycle 1 only.
   Cycles 2-3 ride residual fitness with 18-20 mi peaks.
5. **Consistency over heroics** — a 4-day week done beats a 6-day week skipped.
   80/20: about 80% of run time easy, 20% at MP effort or harder.
```

## Weekly Template (the structural rule)

```
Mon  — Strength A (heavier lower, lunch)  — no run
Tue  — Trail run (easy)
Wed  — Trail run (the QUALITY run on quality weeks: tempo / MP / steady)
Thu  — Trail run (easy)
Fri  — Strength B (lighter, lunch)  — no run
Sat  — Long run  (slider: can shift to Sun if life intervenes)
Sun  — Short recovery run (2-3 mi very easy) — DROPPABLE
```

**Trail block (Tue/Wed/Thu):** Perkiomen Trail behind the office. Target all 3;
floor is 2 of 3. One run is the QUALITY run on quality weeks. Do quality on the
earlier available day. Never the day before the long run.

**Weekend slider:** long run defaults to Saturday; recovery run defaults to
Sunday. Either can shift if needed — always do recovery AFTER long, not before.

**Priority when a week falls apart:** Long run → Quality run → Mon + Fri strength
(never skip both) → 2nd/3rd trail runs (floor is 2 of 3) → Recovery run (drop
first, no guilt).

## Strength Sessions (45 min, lunch)

### Intro Strength A (Weeks 1-2 only — Monday)
- Goblet squat 3 x 8
- Romanian deadlift 3 x 8 light
- Push-ups or bench press 3 x 6-8
- Lat pulldown or assisted pull-up 3 x 8
- 5 min easy bike or row

### Intro Strength B (Weeks 1-2 only — Friday)
- Reverse lunges 2 x 8 each side
- Single-arm dumbbell row 3 x 8 each side
- Overhead press (DB) 3 x 6-8
- Side plank 2 x 20-30 sec each side
- Farmer carry 3 x 30 sec

### Strength A — Monday (heavier lower) — Week 3 onward
- Back squat 3 x 5
- Romanian deadlift 3 x 5
- Bench press 3 x 5
- Pull-ups or ring rows 3 sets

### Strength B — Friday (lighter) — Week 3 onward
- Overhead press (DB) 3 x 6-8
- Single-arm row 3 x 8 each
- Split squat or step-up 2 x 8 each side (light)
- Side plank or Copenhagen plank 2 sets
- Farmer carry 3 x 30 sec

**Rules:** 1-3 reps in reserve, moderate loads. 45-min cap — no metcon. Skip
Strength B in peak/taper weeks.

## Knee/IT Band Prehab (2x/week, 10 min)

After a trail run and once on the weekend. Never right before the long run.

- Single-leg deadlifts: 2 x 8 each side
- Copenhagen planks: 2 x 20-30 sec each side
- Monster walks with band: 2 x 10 steps each direction
- Bulgarian split squats: 2 x 8 each side
- Side-lying hip abduction: 2 x 12 each side
- Single-leg calf raises: 2 x 12 each side

## Pre/Post Run Routine

**Before every run, 5-7 min:** leg swings, walking lunges, glute bridges, calf
raises, high knees, butt kicks, skip with arm drive.

**After every run, 3-5 min:** walk cool down, calf stretch, hip flexor stretch,
figure-four glute stretch, gentle trunk rotation.

---

# Phase 1 — MCM Build (22 weeks)

**Cycle anchor:** race 2026-10-25, week 22 = race week. Week 1 starts
2026-05-25 (Mon, Memorial Day).

**Peak:** ~33-35 mpw. Peak long run: 21-22 mi (week 20, confidence run).

**Structure:** 3 trail runs + 1 long run + 1 short recovery run + 2 strength
days. Quality run defaults to Wednesday; long run defaults to Saturday; recovery
run defaults to Sunday. Floating quality day and weekend slider can shift to
match real life — use drag-to-move.

## Phase 1 Workout Table

> Format: `week | day | type | dist_mi | dur_min | description | intent`
> `type` is one of the workout_type enum values from schema.sql.
> Empty `dist_mi` for non-running workouts.

```
WEEK 1 — Foundation start (Memorial Day kickoff)
Mon | strength_a |     | 45  | Intro Strength A — goblet squat, RDL light, push-ups, lat pulldown, 5min bike/row | Memorial Day kickoff, gentle intro to lifting
Tue | easy       | 3   | 30  | 3 easy trail (Perkiomen) + prehab                            | Aerobic intro, knee prehab
Wed | easy       | 3   | 30  | 3 easy trail (Perkiomen)                                     | Pure aerobic
Thu | easy       | 3   | 30  | 3 easy trail (Perkiomen)                                     | Pure aerobic
Fri | strength_b |     | 45  | Intro Strength B — reverse lunges, DB row, OH press, side plank, farmer carry | Lighter intro lift, 48h before long run
Sat | long       | 6   | 78  | 6 mile long run (run/walk OK)                                | Aerobic base, ease into long-run rhythm
Sun | recovery   | 2   | 24  | 2 mi very easy recovery run                                  | Active recovery, conversational — droppable
WEEK 2
Mon | strength_a |     | 45  | Intro Strength A                                             | Heavier lower, gentle intro
Tue | easy       | 3   | 30  | 3 easy trail (Perkiomen) + prehab                            | Aerobic + knee prehab
Wed | easy       | 3   | 30  | 3 easy trail (Perkiomen)                                     | Pure aerobic
Thu | easy       | 3   | 30  | 3 easy trail (Perkiomen)                                     | Pure aerobic
Fri | strength_b |     | 45  | Intro Strength B                                             | Lighter upper
Sat | long       | 7   | 91  | 7 mile long run                                              | +1mi LR progression
Sun | recovery   | 2   | 24  | 2 mi very easy recovery run                                  | Active recovery — droppable
WEEK 3
Mon | strength_a |     | 45  | Strength A — back squat 3x5, RDL 3x5, bench 3x5, pull-ups (light loads first week full strength) | First full Strength A, light loads
Tue | easy       | 3   | 30  | 3 easy trail (Perkiomen) + prehab                            | Aerobic + prehab
Wed | easy       | 4   | 40  | 4 easy trail + strides                                       | Aerobic + strides for freshness
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B — OH press, single-arm row, split squat, side plank, farmer carry | First full Strength B
Sat | long       | 8   | 104 | 8 mile long run                                              | LR progression
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 4
Mon | strength_a |     | 45  | Strength A — back squat, RDL, bench, pull-ups                | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | tempo      | 4   | 40  | 4mi w/ 2x8min tempo (QUALITY)                                | First tempo work — controlled, stronger than MP
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 9   | 117 | 9 mile long run (fueling starts: 30g/hr)                     | LR progression, first fueling target
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 5 — cutback
Mon | strength_a |     | 45  | Strength A — lighter loads                                   | Recovery loads, hold movement
Tue | easy       | 3   | 30  | 3 easy trail + strides + prehab                              | Cutback aerobic + strides
Wed | easy       | 3   | 30  | 3 easy trail + strides                                       | Cutback midweek
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Cutback aerobic
Fri | strength_b |     | 45  | Strength B — lighter                                         | Recovery loads
Sat | long       | 7   | 91  | 7 mile long run                                              | Cutback LR
Sun | recovery   | 2   | 24  | 2 mi very easy recovery run                                  | Active recovery
WEEK 6
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 5   | 55  | 5mi w/ 3x8min MP effort (QUALITY)                            | MP intro
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 10  | 130 | 10 mile long run (short hills, 40g/hr)                       | First hill exposure, fueling step up
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 7
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 5   | 55  | 5mi w/ 20min steady block (QUALITY)                          | Sustained MP effort
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 11  | 143 | 11 mile long run (45g/hr)                                    | LR progression
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 8
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | tempo      | 6   | 60  | 6mi w/ 4x5min tempo (QUALITY)                                | Tempo intervals
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 12  | 156 | 12 mile long run (hilly, 45g/hr)                             | Hilly LR for MCM prep
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 9 — cutback
Mon | strength_a |     | 45  | Strength A — lighter                                         | Recovery loads
Tue | easy       | 3   | 30  | 3 easy trail + prehab                                        | Cutback aerobic
Wed | easy       | 4   | 40  | 4mi trail progression run                                    | Light intensity exposure
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Cutback aerobic
Fri | strength_b |     | 45  | Strength B — lighter                                         | Recovery loads
Sat | long       | 10  | 130 | 10 mile long run                                             | Cutback LR
Sun | recovery   | 2   | 24  | 2 mi very easy recovery run                                  | Active recovery
WEEK 10
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 6   | 66  | 6mi w/ 2x12min MP effort (QUALITY)                           | MP volume up
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 14  | 182 | 14 mile long run (50g/hr)                                    | LR progression, fueling
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 11
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | tempo      | 6   | 60  | 6mi w/ 5x3min threshold (QUALITY)                            | Threshold work
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 15  | 195 | 15 mile long run (hilly, 50g/hr)                             | Hilly LR + fueling
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 12 — cutback
Mon | strength_a |     | 45  | Strength A — lighter                                         | Recovery loads
Tue | easy       | 4   | 40  | 4 easy trail + strides + prehab                              | Cutback aerobic + strides
Wed | easy       | 4   | 40  | 4 easy trail + strides                                       | Cutback midweek
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Cutback aerobic
Fri | strength_b |     | 45  | Strength B — lighter                                         | Recovery loads
Sat | long       | 12  | 156 | 12 mile long run                                             | Cutback LR
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 13
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 7   | 77  | 7mi w/ 2x15min MP effort (QUALITY)                           | MP volume
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 16  | 208 | 16 mile long run (55g/hr)                                    | LR progression w/ fuel
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 14
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 6   | 60  | 6mi w/ 25min steady block (QUALITY)                          | Sustained MP block
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 17  | 221 | 17 mile long run (60g/hr)                                    | LR progression
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 15
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | tempo      | 6   | 60  | 6mi w/ 6x3min threshold (QUALITY)                            | Threshold work
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B                                                   | Lighter upper
Sat | long       | 18  | 234 | 18 mile long run (hilly, 60g/hr)                             | Hilly LR + fueling
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 16 — cutback
Mon | strength_a |     | 45  | Strength A — lighter                                         | Recovery loads
Tue | easy       | 4   | 40  | 4 easy trail + strides + prehab                              | Cutback aerobic + strides
Wed | easy       | 4   | 40  | 4 easy trail + strides                                       | Cutback midweek
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Cutback aerobic
Fri | strength_b |     | 45  | Strength B — lighter                                         | Recovery loads
Sat | long       | 13  | 169 | 13 mile long run                                             | Cutback LR
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 17
Mon | strength_a |     | 45  | Strength A                                                   | Heavier lower
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 7   | 77  | 7mi w/ 3x15min MP effort (QUALITY)                           | MP work
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B reduced                                           | Reduced loads
Sat | long       | 16  | 208 | 16 mile LR w/ final 3 at MP effort (65g/hr)                  | MP-tail LR, fueling
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 18 — first 20
Mon | strength_a |     | 45  | Strength A reduced                                           | Reduced loads
Tue | easy       | 4   | 40  | 4 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 7   | 77  | 7mi w/ 4x10min MP effort (QUALITY)                           | MP intervals
Thu | easy       | 4   | 40  | 4 easy trail                                                 | Aerobic
Fri | strength_b |     | 45  | Strength B reduced                                           | Reduced loads
Sat | long       | 20  | 260 | 20 mile long run (70g/hr — full race rehearsal)              | First 20mi confidence run + fuel rehearsal
Sun | recovery   | 2   | 24  | 2 mi very easy walk/jog                                      | Active recovery, very gentle
WEEK 19 — cutback before peak
Mon | strength_a |     | 45  | Strength A — lighter                                         | Recovery loads
Tue | easy       | 3   | 30  | 3 easy trail + prehab                                        | Cutback aerobic
Wed | easy       | 5   | 50  | 5mi trail progression run                                    | Light intensity, cutback
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Cutback aerobic
Fri | strength_b |     | 45  | Strength B — lighter                                         | Recovery loads
Sat | long       | 14  | 182 | 14 mile long run                                             | Cutback LR
Sun | recovery   | 3   | 36  | 3 mi very easy recovery run                                  | Active recovery
WEEK 20 — PEAK (confidence run)
Mon | strength_a |     | 30  | Strength A very light                                        | Movement only, very light loads
Tue | easy       | 3   | 30  | 3 easy trail + prehab                                        | Aerobic + prehab
Wed | mp_long    | 6   | 66  | 6mi w/ 2x20min MP effort (QUALITY)                           | MP confirmation
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Aerobic
Fri | rest       |     | 20  | Optional mobility — no strength                              | Pre-peak rest
Sat | long       | 22  | 286 | 21-22 mile peak LR (75g/hr — full dress rehearsal) — KNEE RULE: any IT band/knee pain in W17-19 caps this at 20mi | Peak confidence run, full race-day fuel
Sun | recovery   | 2   | 24  | 2 mi very easy walk                                          | Peak recovery
WEEK 21 — taper
Mon | strength_a |     | 30  | Light Strength A                                             | Taper loads
Tue | easy       | 3   | 30  | 3 easy trail + prehab                                        | Aerobic
Wed | mp_long    | 5   | 50  | 5mi w/ 2x15min MP effort (QUALITY)                           | MP touch, taper
Thu | easy       | 3   | 30  | 3 easy trail                                                 | Aerobic
Fri | rest       |     | 20  | Optional mobility — no strength                              | Taper rest
Sat | long       | 12  | 156 | 12 mile long run                                             | Taper LR
Sun | recovery   | 2   | 24  | 2 mi very easy recovery run                                  | Active recovery
WEEK 22 — RACE WEEK
Mon | mp_long    | 3   | 30  | 3 easy w/ 2x1mi MP effort                                    | Race-week sharpener, no strength
Tue | rest       |     |     | REST                                                         | Recovery
Wed | easy       | 3   | 30  | 3 easy + strides                                             | Loose legs, sharpening
Thu | easy       | 3   | 30  | 2-3 easy                                                     | Stay loose
Fri | rest       |     |     | REST                                                         | Pre-race rest
Sat | easy       | 2   | 20  | 20 min shakeout                                              | Race tomorrow
Sun | race       | 26.2| 300 | 🎖️ MARINE CORPS MARATHON                                     | Race day. Sub-5:00. Healthy. Enjoy.
```

---

# Phase 2 — Disney Build (11 weeks)

> **PRELIMINARY** — carried over from v2.0 plan. Will be re-anchored after MCM
> once recovery response is known. Treat as provisional structure, not literal
> prescription.

**Cycle anchor:** race 2027-01-10. Week 1 starts 2026-10-26 (day after MCM).

**Peak:** ~37-39 mpw. Peak long run: 18 mi (week 8).

**Approach:** ride residual MCM fitness; party marathon, finish and enjoy.

```
WEEK 1 — post-MCM recovery
Mon | rest       |     |     | PRELIMINARY — Walking, mobility                              | Recovery
Tue | rest       |     |     | PRELIMINARY — Walking, mobility                              | Recovery
Wed | rest       |     |     | PRELIMINARY — Walking                                        | Recovery
Thu | easy       | 2   | 25  | PRELIMINARY — Optional 20-30min shakeout                     | Optional, only if legs feel good
Fri | rest       |     |     | PRELIMINARY — Rest                                           | Recovery
Sat | easy       | 2   | 25  | PRELIMINARY — Optional 20-30min shakeout                     | Optional
Sun | rest       |     |     | PRELIMINARY — Mobility                                       | Recovery
WEEK 2 — recovery continued
Mon | rest       |     |     | PRELIMINARY — Mobility                                       | Recovery
Tue | easy       | 3   | 30  | PRELIMINARY — 3 easy                                         | Reintroduce running
Wed | rest       |     | 20  | PRELIMINARY — Mobility                                       | Easy
Thu | easy       | 3   | 30  | PRELIMINARY — 3 easy                                         | Aerobic
Fri | rest       |     |     | PRELIMINARY — Rest                                           | —
Sat | easy       | 4   | 40  | PRELIMINARY — 4 easy                                         | Light long
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 3 — rebuild begins
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — light loads                       | Reintroduce strength
Wed | easy       | 4   | 36  | PRELIMINARY — 4 easy + strides                               | Strides
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — light                             | Lighter upper
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Pre-LR
Sat | long       | 8   | 104 | PRELIMINARY — 8 mile long run                                | Aerobic rebuild
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 4
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pure aerobic
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 10  | 130 | PRELIMINARY — 10 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 5
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | mp_long    | 5   | 55  | PRELIMINARY — 5mi w/ 3 x 8min MP                             | MP reintroduction
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 12  | 156 | PRELIMINARY — 12 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 6
Mon | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | tempo      | 6   | 60  | PRELIMINARY — 6mi w/ 3 x 8min tempo                          | Tempo
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 14  | 182 | PRELIMINARY — 14 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 7 — cutback
Mon | easy       | 3   | 27  | PRELIMINARY — 3 easy                                         | Cutback
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — lighter                           | Recovery loads
Wed | easy       | 5   | 45  | PRELIMINARY — 5 easy + strides                               | Cutback midweek
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — lighter                           | Recovery loads
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Pre-LR
Sat | long       | 10  | 130 | PRELIMINARY — 10 mile long run                               | Cutback LR
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 8 — peak
Mon | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | mp_long    | 6   | 66  | PRELIMINARY — 6mi w/ 25min MP                                | MP confirmation
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 18  | 234 | PRELIMINARY — 18 mile peak LR (fuel 65g/hr)                  | Peak — fuel rehearsal
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 9 — dress rehearsal
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — moderate                          | Reduced loads
Wed | mp_long    | 6   | 66  | PRELIMINARY — 6mi w/ 3 x 10min MP                            | MP touch
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — moderate                          | Reduced loads
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 14  | 182 | PRELIMINARY — 14 mile LR w/ MP segments + fuel test          | Dress rehearsal
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 10 — taper
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_b |     | 30  | PRELIMINARY — Light strength                                 | Movement only
Wed | tempo      | 5   | 50  | PRELIMINARY — 5mi w/ 10min tempo                             | Light intensity
Thu | rest       |     | 20  | PRELIMINARY — Mobility                                       | Active recovery
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy + strides                               | Strides
Sat | long       | 9   | 117 | PRELIMINARY — 9 mile long run                                | Taper LR
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 11 — RACE WEEK
Mon | mp_long    | 4   | 40  | PRELIMINARY — 4 easy w/ 2 x 1mi MP effort                    | MP touch
Tue | rest       |     | 20  | PRELIMINARY — Mobility                                       | —
Wed | easy       | 3   | 27  | PRELIMINARY — 3 easy                                         | Aerobic
Thu | easy       | 2   | 20  | PRELIMINARY — 2 easy + strides                               | Strides
Fri | rest       |     |     | PRELIMINARY — Travel/rest                                    | Rest
Sat | easy       | 2   | 20  | PRELIMINARY — 20 min shakeout                                | Pre-race shakeout
Sun | race       | 26.2| 300 | PRELIMINARY — 🏰 WALT DISNEY WORLD MARATHON                  | Race day. Sub-5:00. Enjoy.
```

---

# Phase 3 — Delaware Build (13 weeks)

> **PRELIMINARY** — carried over from v2.0 plan. Will be re-anchored after MCM
> once recovery response is known. Treat as provisional structure, not literal
> prescription.

**Cycle anchor:** race 2027-04-11. Week 1 starts 2027-01-11 (day after Disney).

**Peak:** ~37-40 mpw. Peak long run: 18-20 mi (week 10).

**Approach:** three-block — recover (3w), rebuild (6w), specific (4w). Decision
point at end of week 3.

```
WEEK 1 — post-Disney recovery
Mon | rest       |     |     | PRELIMINARY — Walking, mobility                              | Recovery
Tue | rest       |     |     | PRELIMINARY — Walking                                        | Recovery
Wed | rest       |     |     | PRELIMINARY — Walking                                        | Recovery
Thu | easy       | 2   | 25  | PRELIMINARY — Optional 20-30min shakeout                     | Optional
Fri | rest       |     |     | PRELIMINARY — Rest                                           | —
Sat | easy       | 2   | 25  | PRELIMINARY — Optional 20-30min shakeout                     | Optional
Sun | rest       |     |     | PRELIMINARY — Mobility                                       | —
WEEK 2
Mon | rest       |     |     | PRELIMINARY — Mobility                                       | Recovery
Tue | easy       | 3   | 30  | PRELIMINARY — 3 easy                                         | Reintroduce
Wed | strength_b |     | 30  | PRELIMINARY — Light strength                                 | Movement only
Thu | easy       | 3   | 30  | PRELIMINARY — 3 easy                                         | Aerobic
Fri | rest       |     |     | PRELIMINARY — Rest                                           | —
Sat | easy       | 5   | 50  | PRELIMINARY — 5 easy                                         | Light long
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 3 — DECISION POINT (end of week)
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — light                             | Reintroduce strength
Wed | easy       | 4   | 36  | PRELIMINARY — 4 easy + strides                               | Strides
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — light                             | Lighter upper
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Pre-LR
Sat | long       | 8   | 104 | PRELIMINARY — 8 mile long run + HONEST CHECK-IN              | Decision point — see plan rule
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 4
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pure aerobic
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 10  | 130 | PRELIMINARY — 10 mile long run                               | LR rebuild
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 5
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | mp_long    | 5   | 55  | PRELIMINARY — 5mi w/ 3 x 8min MP                             | MP reintroduction
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 12  | 156 | PRELIMINARY — 12 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 6
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | tempo      | 6   | 60  | PRELIMINARY — 6mi w/ 3 x 8min tempo                          | Tempo
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 14  | 182 | PRELIMINARY — 14 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 7 — cutback
Mon | easy       | 3   | 27  | PRELIMINARY — 3 easy                                         | Cutback
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — lighter                           | Recovery loads
Wed | easy       | 5   | 45  | PRELIMINARY — 5 easy + strides                               | Cutback midweek
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — lighter                           | Recovery loads
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Pre-LR
Sat | long       | 10  | 130 | PRELIMINARY — 10 mile long run                               | Cutback LR
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 8
Mon | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | mp_long    | 6   | 66  | PRELIMINARY — 6mi w/ 3 x 12min MP                            | MP volume
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 6   | 54  | PRELIMINARY — 6 easy                                         | Pre-LR
Sat | long       | 15  | 195 | PRELIMINARY — 15 mile long run                               | LR progression
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 9
Mon | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | tempo      | 6   | 60  | PRELIMINARY — 6mi w/ 3 x 10min tempo                         | Tempo
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 6   | 54  | PRELIMINARY — 6 easy                                         | Pre-LR
Sat | long       | 17  | 221 | PRELIMINARY — 17 mile long run (fuel 65g/hr)                 | LR progression w/ fuel
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 10 — peak
Mon | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Aerobic
Tue | strength_a |     | 60  | PRELIMINARY — Strength A                                     | Heavier lower
Wed | mp_long    | 6   | 66  | PRELIMINARY — 6mi w/ 25min MP                                | MP confirmation
Thu | strength_b |     | 60  | PRELIMINARY — Strength B                                     | Lighter upper
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 19  | 247 | PRELIMINARY — 19 mile peak LR (fuel 70g/hr)                  | Peak — see decision rule
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 11 — dress rehearsal
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_a |     | 45  | PRELIMINARY — Strength A — moderate                          | Reduced loads
Wed | mp_long    | 6   | 66  | PRELIMINARY — 6mi w/ 3 x 10min MP                            | MP touch
Thu | strength_b |     | 45  | PRELIMINARY — Strength B — moderate                          | Reduced loads
Fri | easy       | 5   | 45  | PRELIMINARY — 5 easy                                         | Pre-LR
Sat | long       | 14  | 182 | PRELIMINARY — 14 mile LR w/ MP segments + fuel test          | Dress rehearsal
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 12 — taper
Mon | easy       | 4   | 36  | PRELIMINARY — 4 easy                                         | Aerobic
Tue | strength_b |     | 30  | PRELIMINARY — Light strength                                 | Movement only
Wed | tempo      | 5   | 50  | PRELIMINARY — 5mi w/ 10min tempo                             | Light intensity
Thu | rest       |     | 20  | PRELIMINARY — Mobility                                       | Active recovery
Fri | easy       | 4   | 36  | PRELIMINARY — 4 easy + strides                               | Strides
Sat | long       | 10  | 130 | PRELIMINARY — 10 mile long run                               | Taper LR
Sun | rest       |     |     | PRELIMINARY — Recovery                                       | —
WEEK 13 — RACE WEEK
Mon | mp_long    | 4   | 40  | PRELIMINARY — 4 easy w/ 2 x 1mi MP effort                    | MP touch
Tue | rest       |     | 20  | PRELIMINARY — Mobility                                       | —
Wed | easy       | 3   | 27  | PRELIMINARY — 3 easy                                         | Aerobic
Thu | easy       | 2   | 20  | PRELIMINARY — 2 easy + strides                               | Strides
Fri | rest       |     |     | PRELIMINARY — Travel/rest                                    | Rest
Sat | easy       | 2   | 20  | PRELIMINARY — 20 min shakeout                                | Pre-race shakeout
Sun | race       | 26.2| 300 | PRELIMINARY — 🌊 COASTAL DELAWARE MARATHON                   | Race day. Sub-5:00. Enjoy. Trilogy done.
```

## Decision Rules (encoded as constraints, agents reference these)

```yaml
- name: phase1_peak_knee_check
  trigger: "Phase 1, Week 20 long run"
  rule: "If any knee pain in weeks 17-19, peak long run (W20) caps at 20mi
         instead of 22mi."
  action: "Plan Adapter agent flags this on the W19 long-run review."

- name: phase3_decision_point
  trigger: "Phase 3, Week 3 long run"
  rule: |
    End of week 3 honest assessment:
      - Felt great: run plan as written.
      - Some lingering fatigue: extend recovery 1w, compress rebuild,
        cap peak at 18mi.
      - Feels rough: easy-effort race, cap peak 16-18mi, cut strength volume.
  action: "Daily Coach prompts decision question on Sat eve of W3."

- name: stacking_warning
  trigger: "user moves a workout"
  rule: |
    Hard days should not stack within 24h:
      - Long run + strength_a same/next day = warning
      - Tempo/mp_long + long run within 48h = warning
      - Strength_a + Strength_b same day = warning
  action: "Plan Adapter surfaces in proposal."
```
