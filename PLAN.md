# Marathon Trilogy Training Plan v2.0

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
  Rule: any knee pain in weeks 19-22 of Phase 1 → cap peak long run at 20mi.
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
2. **Sequencing matters** — long runs and strength are spaced to avoid stacking
   hard days. Quality midweek, not Monday. Heavier strength early in the week,
   far from the long run.
3. **Knee protection first** — specific glute med and hip stability prehab
   2x/week, not generic core work.
4. **Confidence on MCM only** — 21-22 mi peak long run for cycle 1 only.
   Cycles 2-3 ride residual fitness with 18-20 mi peaks.
5. **Honest checkpoints** — decision points built in, not emotional calls in
   the moment. End of week 3 post-Disney is a key check-in.
6. **80/20** — about 80% of run time in Z1-Z2, 20% at MP effort or harder.
```

## Weekly Template (the structural rule)

```
Mon  — Easy recovery run (3-5mi) or full rest
Tue  — Strength A (heavier lower: squats, RDL, bench, pulls)
Wed  — Quality run (tempo, MP effort, intervals) OR easy + strides
Thu  — Strength B (lighter upper + accessories: press, splits, cleans, carries)
Fri  — Easy or medium-long aerobic (4-6mi)
Sat  — Long run
Sun  — Recovery / mobility / family
```

**Why:** Tuesday is 4 days from the long run, Thursday is 48h. Quality
Wednesday gives a full easy day before Saturday. Hard-day stacking is the
single biggest injury risk.

## Strength Sessions

### Strength A — Tuesday (heavier lower)
- Back squat, 3 x 5
- Romanian deadlift, 3 x 5
- Bench press, 3 x 5
- Pull-ups or ring rows, 3 sets
- Optional 6-8 min easy metcon (carries, bike, row)

### Strength B — Thursday (lighter, upper + accessories)
- Overhead press or incline press, 3 x 5
- Split squat or step-up, 2-3 sets each side
- Power clean or hang power clean, 5 x 2 light-moderate
- Farmer carry or suitcase carry, 3 rounds
- Single-arm row or pull-up variation, 3 sets

**Rules:** 1-3 reps in reserve. Moderate loads. Skip or lighten in peak running
weeks.

## Knee/IT Band Prehab (2x/week, 10 min)

After easy runs or on strength days. Not before long runs.

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

# Phase 1 — MCM Build (28 weeks)

**Cycle anchor:** race 2026-10-25, week 28 = race week. Week 1 starts
2026-04-13 (Mon).

**Peak:** ~40-42 mpw. Peak long run: 21-22 mi (week 23, confidence run).

## Phase 1 Workout Table

> Format: `week | day | type | dist_mi | dur_min | description | intent`
> `type` is one of the workout_type enum values from schema.sql.
> Empty `dist_mi` for non-running workouts.

```
WEEK 1 — Foundation start
Mon | easy       | 4   | 35  | 4 easy + 4 strides                        | Aerobic intro, neuromuscular activation via strides
Tue | strength_a |     | 60  | Strength A — squats, RDL, bench, pulls    | Heavier lower far from long run
Wed | easy       | 4   | 36  | 4 easy                                    | Pure aerobic
Thu | strength_b |     | 60  | Strength B — press, splits, cleans, carry | Lighter upper, 48h before LR
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR easy
Sat | long       | 6   | 78  | 6 mile long run                           | Aerobic base, conversational pace
Sun | rest       |     |     | Mobility + family day                     | Active recovery

WEEK 2
Mon | easy       | 4   | 35  | 4 easy + 6 strides                        | Aerobic + neuromuscular
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | easy       | 4   | 36  | 4 easy                                    | Pure aerobic
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 4   | 36  | 4 easy, last 10 min steady                | Steady finish primes Saturday
Sat | long       | 7   | 91  | 7 mile long run                           | +1mi LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 3
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 4   | 40  | 4mi w/ 2 x 8min tempo                     | First tempo work, midweek by design
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 9   | 117 | 9 mile long run                           | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 4 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback week, drop volume
Tue | strength_a |     | 45  | Strength A — lighter loads                 | Recovery loads, hold movement
Wed | easy       | 4   | 36  | 4 easy + strides                          | Strides for freshness
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 3   | 27  | 3 easy                                    | Pre-LR easy
Sat | long       | 7   | 91  | 7 mile long run                           | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 5
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 5   | 55  | 5mi w/ 3 x 8min MP effort                 | MP intro
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Aerobic
Sat | long       | 10  | 130 | 10 mile LR (include 2 short hills)        | First hill exposure for MCM prep
Sun | rest       |     |     | Recovery                                  | —

WEEK 6
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 5   | 50  | 5mi w/ 20min steady middle block          | Steady-state aerobic
Thu | strength_b |     | 60  | Strength B + carries                      | Carries for posture/grip
Fri | easy       | 5   | 45  | 5 easy + strides                          | Strides
Sat | long       | 11  | 143 | 11 mile long run                          | LR progression
Sun | rest       |     |     | Mobility                                  | —

WEEK 7
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 3 x 10min MP effort                | MP volume up
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 12  | 156 | 12 mile LR (hilly route)                  | Hilly LR for MCM prep
Sun | rest       |     |     | Recovery                                  | —

WEEK 8 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | tempo      | 4   | 40  | 4mi progression run                       | Light intensity exposure
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 9   | 117 | 9 mile long run                           | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 9
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 4 x 5min tempo                     | Tempo intervals
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 13  | 169 | 13 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 10
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 25min MP block                     | Sustained MP
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy + strides                          | Strides
Sat | long       | 14  | 182 | 14 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 11
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | hills      | 6   | 60  | 6mi w/ 6 x 60sec hill repeats             | MCM-specific hill durability
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 15  | 195 | 15 mile LR (hilly route)                  | Hilly LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 12 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | easy       | 5   | 45  | 5 easy + strides                          | Cutback Wed
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 11  | 143 | 11 mile long run                          | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 13
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 7   | 77  | 7mi w/ 3 x 12min MP                       | MP volume
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 16  | 208 | 16 mile long run (fuel: 55g/hr)           | First fueling target
Sun | rest       |     |     | Recovery                                  | —

WEEK 14
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 3 x 10min tempo                    | Tempo
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 17  | 221 | 17 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 15
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | hills      | 6   | 60  | 6mi w/ 5 x 90sec hill repeats             | Hill durability
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 18  | 234 | 18 mile LR (hilly, fuel 65g/hr)           | Fueling step up + hills
Sun | rest       |     |     | Recovery                                  | —

WEEK 16 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | tempo      | 5   | 50  | 5mi progression                           | Light tempo
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 12  | 156 | 12 mile long run                          | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 17
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 7   | 77  | 7mi w/ 4 x 10min MP                       | MP work
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 16  | 208 | 16 mile LR w/ last 5 at MP                | MP-tail LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 18
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 7   | 70  | 7mi w/ 3 x 12min tempo                    | Tempo volume
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 19  | 247 | 19 mile long run (fuel 70g/hr)            | Long aerobic, fueling
Sun | rest       |     |     | Recovery                                  | —

WEEK 19
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 25min MP                           | MP confirmation
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 20  | 260 | 20 mile LR — rehearsal #1                 | First 20mi confidence run
Sun | rest       |     |     | Recovery                                  | —

WEEK 20 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | easy       | 5   | 45  | 5 easy + strides                          | Cutback midweek
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 13  | 169 | 13 mile long run                          | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 21
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 7   | 77  | 7mi w/ 3 x 15min MP                       | Race-effort prep
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 18  | 234 | 18 mile LR w/ last 6 at MP                | MP-heavy LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 22
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 2 x 15min tempo                    | Tempo
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 16  | 208 | 16 mile LR (knee check before W23)        | KNEE CHECK — see injury rule
Sun | rest       |     |     | Recovery                                  | —

WEEK 23 — peak (decision point: knee = 22, no knee = 21)
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 20min MP                           | MP confirmation
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery into peak
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 22  | 286 | 22 mile peak LR (fuel 75g/hr) — confidence | Peak confidence run
Sun | rest       |     |     | Recovery                                  | —

WEEK 24 — recovery from peak
Mon | rest       |     |     | Off or 3 recovery miles                   | Peak recovery
Tue | strength_b |     | 30  | Light technique strength                  | Movement only
Wed | easy       | 5   | 45  | 5 easy                                    | Aerobic
Thu | rest       |     | 20  | Mobility or very light strength           | Active recovery
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 14  | 182 | 14 mile long run                          | Recovery LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 25 — taper begins
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 45  | Light strength                            | Reduced volume
Wed | mp_long    | 6   | 60  | 6mi w/ 2 x 15min MP                       | MP touch
Thu | rest       |     | 20  | Mobility                                  | Active recovery
Fri | easy       | 5   | 45  | 5 easy + strides                          | Strides for sharpness
Sat | long       | 12  | 156 | 12 mile long run                          | Taper LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 26
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_b |     | 30  | Very light strength                       | Movement only
Wed | tempo      | 5   | 50  | 5mi w/ 10min tempo                        | Light intensity
Thu | rest       |     | 20  | Mobility                                  | Active recovery
Fri | easy       | 4   | 36  | 4 easy + strides                          | Sharpness
Sat | long       | 8   | 72  | 8 easy miles                              | Short LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 27 — sharpen
Mon | mp_long    | 4   | 40  | 4 easy w/ 2 x 1mi MP effort               | MP touch
Tue | rest       |     | 20  | Mobility                                  | —
Wed | easy       | 3   | 27  | 3 easy                                    | Aerobic
Thu | easy       | 3   | 27  | 2-3 easy + strides                        | Strides
Fri | rest       |     |     | Off                                       | Rest
Sat | easy       | 2   | 20  | 20-30 min shakeout                        | Pre-race shakeout
Sun | rest       |     |     | Rest                                      | —

WEEK 28 — RACE WEEK
Mon | easy       | 3   | 27  | 3 easy                                    | Race week opener
Tue | easy       | 3   | 27  | 3 easy + strides                          | Strides
Wed | rest       |     |     | Off                                       | Rest
Thu | easy       | 2   | 20  | 2 easy                                    | Loosen up
Fri | rest       |     |     | Off                                       | Rest
Sat | easy       | 2   | 20  | 20 min shakeout                           | Pre-race shakeout
Sun | race       | 26.2| 300 | 🎖️ MARINE CORPS MARATHON                  | Race day. Sub-5:00. Enjoy.
```

---

# Phase 2 — Disney Build (11 weeks)

**Cycle anchor:** race 2027-01-10. Week 1 starts 2026-10-26 (day after MCM).

**Peak:** ~37-39 mpw. Peak long run: 18 mi (week 8).

**Approach:** ride residual MCM fitness; party marathon, finish and enjoy.

```
WEEK 1 — post-MCM recovery
Mon | rest       |     |     | Walking, mobility                         | Recovery
Tue | rest       |     |     | Walking, mobility                         | Recovery
Wed | rest       |     |     | Walking                                   | Recovery
Thu | easy       | 2   | 25  | Optional 20-30min shakeout                | Optional, only if legs feel good
Fri | rest       |     |     | Rest                                      | Recovery
Sat | easy       | 2   | 25  | Optional 20-30min shakeout                | Optional
Sun | rest       |     |     | Mobility                                  | Recovery

WEEK 2 — recovery continued
Mon | rest       |     |     | Mobility                                  | Recovery
Tue | easy       | 3   | 30  | 3 easy                                    | Reintroduce running
Wed | rest       |     | 20  | Mobility                                  | Easy
Thu | easy       | 3   | 30  | 3 easy                                    | Aerobic
Fri | rest       |     |     | Rest                                      | —
Sat | easy       | 4   | 40  | 4 easy                                    | Light long
Sun | rest       |     |     | Recovery                                  | —

WEEK 3 — rebuild begins
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 45  | Strength A — light loads                  | Reintroduce strength
Wed | easy       | 4   | 36  | 4 easy + strides                          | Strides
Thu | strength_b |     | 45  | Strength B — light                        | Lighter upper
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 8   | 104 | 8 mile long run                           | Aerobic rebuild
Sun | rest       |     |     | Recovery                                  | —

WEEK 4
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | easy       | 5   | 45  | 5 easy                                    | Pure aerobic
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 10  | 130 | 10 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 5
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 5   | 55  | 5mi w/ 3 x 8min MP                        | MP reintroduction
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 12  | 156 | 12 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 6
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 3 x 8min tempo                     | Tempo
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 14  | 182 | 14 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 7 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | easy       | 5   | 45  | 5 easy + strides                          | Cutback midweek
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 10  | 130 | 10 mile long run                          | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 8 — peak
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 25min MP                           | MP confirmation
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 18  | 234 | 18 mile peak LR (fuel 65g/hr)             | Peak — fuel rehearsal
Sun | rest       |     |     | Recovery                                  | —

WEEK 9 — dress rehearsal
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 45  | Strength A — moderate                     | Reduced loads
Wed | mp_long    | 6   | 66  | 6mi w/ 3 x 10min MP                       | MP touch
Thu | strength_b |     | 45  | Strength B — moderate                     | Reduced loads
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 14  | 182 | 14 mile LR w/ MP segments + fuel test     | Dress rehearsal
Sun | rest       |     |     | Recovery                                  | —

WEEK 10 — taper
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_b |     | 30  | Light strength                            | Movement only
Wed | tempo      | 5   | 50  | 5mi w/ 10min tempo                        | Light intensity
Thu | rest       |     | 20  | Mobility                                  | Active recovery
Fri | easy       | 4   | 36  | 4 easy + strides                          | Strides
Sat | long       | 9   | 117 | 9 mile long run                           | Taper LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 11 — RACE WEEK
Mon | mp_long    | 4   | 40  | 4 easy w/ 2 x 1mi MP effort               | MP touch
Tue | rest       |     | 20  | Mobility                                  | —
Wed | easy       | 3   | 27  | 3 easy                                    | Aerobic
Thu | easy       | 2   | 20  | 2 easy + strides                          | Strides
Fri | rest       |     |     | Travel/rest                               | Rest
Sat | easy       | 2   | 20  | 20 min shakeout                           | Pre-race shakeout
Sun | race       | 26.2| 300 | 🏰 WALT DISNEY WORLD MARATHON              | Race day. Sub-5:00. Enjoy.
```

---

# Phase 3 — Delaware Build (13 weeks)

**Cycle anchor:** race 2027-04-11. Week 1 starts 2027-01-11 (day after Disney).

**Peak:** ~37-40 mpw. Peak long run: 18-20 mi (week 10).

**Approach:** three-block — recover (3w), rebuild (6w), specific (4w). Decision
point at end of week 3.

```
WEEK 1 — post-Disney recovery
Mon | rest       |     |     | Walking, mobility                         | Recovery
Tue | rest       |     |     | Walking                                   | Recovery
Wed | rest       |     |     | Walking                                   | Recovery
Thu | easy       | 2   | 25  | Optional 20-30min shakeout                | Optional
Fri | rest       |     |     | Rest                                      | —
Sat | easy       | 2   | 25  | Optional 20-30min shakeout                | Optional
Sun | rest       |     |     | Mobility                                  | —

WEEK 2
Mon | rest       |     |     | Mobility                                  | Recovery
Tue | easy       | 3   | 30  | 3 easy                                    | Reintroduce
Wed | strength_b |     | 30  | Light strength                            | Movement only
Thu | easy       | 3   | 30  | 3 easy                                    | Aerobic
Fri | rest       |     |     | Rest                                      | —
Sat | easy       | 5   | 50  | 5 easy                                    | Light long
Sun | rest       |     |     | Recovery                                  | —

WEEK 3 — DECISION POINT (end of week)
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 45  | Strength A — light                        | Reintroduce strength
Wed | easy       | 4   | 36  | 4 easy + strides                          | Strides
Thu | strength_b |     | 45  | Strength B — light                        | Lighter upper
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 8   | 104 | 8 mile long run + HONEST CHECK-IN         | Decision point — see plan rule
Sun | rest       |     |     | Recovery                                  | —

WEEK 4
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | easy       | 5   | 45  | 5 easy                                    | Pure aerobic
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 10  | 130 | 10 mile long run                          | LR rebuild
Sun | rest       |     |     | Recovery                                  | —

WEEK 5
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 5   | 55  | 5mi w/ 3 x 8min MP                        | MP reintroduction
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 12  | 156 | 12 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 6
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 3 x 8min tempo                     | Tempo
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 14  | 182 | 14 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 7 — cutback
Mon | easy       | 3   | 27  | 3 easy                                    | Cutback
Tue | strength_a |     | 45  | Strength A — lighter                      | Recovery loads
Wed | easy       | 5   | 45  | 5 easy + strides                          | Cutback midweek
Thu | strength_b |     | 45  | Strength B — lighter                      | Recovery loads
Fri | easy       | 4   | 36  | 4 easy                                    | Pre-LR
Sat | long       | 10  | 130 | 10 mile long run                          | Cutback LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 8
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 3 x 12min MP                       | MP volume
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 15  | 195 | 15 mile long run                          | LR progression
Sun | rest       |     |     | Recovery                                  | —

WEEK 9
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | tempo      | 6   | 60  | 6mi w/ 3 x 10min tempo                    | Tempo
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 6   | 54  | 6 easy                                    | Pre-LR
Sat | long       | 17  | 221 | 17 mile long run (fuel 65g/hr)            | LR progression w/ fuel
Sun | rest       |     |     | Recovery                                  | —

WEEK 10 — peak
Mon | easy       | 5   | 45  | 5 easy                                    | Aerobic
Tue | strength_a |     | 60  | Strength A                                | Heavier lower
Wed | mp_long    | 6   | 66  | 6mi w/ 25min MP                           | MP confirmation
Thu | strength_b |     | 60  | Strength B                                | Lighter upper
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 19  | 247 | 19 mile peak LR (fuel 70g/hr)             | Peak — see decision rule
Sun | rest       |     |     | Recovery                                  | —

WEEK 11 — dress rehearsal
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_a |     | 45  | Strength A — moderate                     | Reduced loads
Wed | mp_long    | 6   | 66  | 6mi w/ 3 x 10min MP                       | MP touch
Thu | strength_b |     | 45  | Strength B — moderate                     | Reduced loads
Fri | easy       | 5   | 45  | 5 easy                                    | Pre-LR
Sat | long       | 14  | 182 | 14 mile LR w/ MP segments + fuel test     | Dress rehearsal
Sun | rest       |     |     | Recovery                                  | —

WEEK 12 — taper
Mon | easy       | 4   | 36  | 4 easy                                    | Aerobic
Tue | strength_b |     | 30  | Light strength                            | Movement only
Wed | tempo      | 5   | 50  | 5mi w/ 10min tempo                        | Light intensity
Thu | rest       |     | 20  | Mobility                                  | Active recovery
Fri | easy       | 4   | 36  | 4 easy + strides                          | Strides
Sat | long       | 10  | 130 | 10 mile long run                          | Taper LR
Sun | rest       |     |     | Recovery                                  | —

WEEK 13 — RACE WEEK
Mon | mp_long    | 4   | 40  | 4 easy w/ 2 x 1mi MP effort               | MP touch
Tue | rest       |     | 20  | Mobility                                  | —
Wed | easy       | 3   | 27  | 3 easy                                    | Aerobic
Thu | easy       | 2   | 20  | 2 easy + strides                          | Strides
Fri | rest       |     |     | Travel/rest                               | Rest
Sat | easy       | 2   | 20  | 20 min shakeout                           | Pre-race shakeout
Sun | race       | 26.2| 300 | 🌊 COASTAL DELAWARE MARATHON               | Race day. Sub-5:00. Enjoy. Trilogy done.
```

## Decision Rules (encoded as constraints, agents reference these)

```yaml
- name: phase1_peak_knee_check
  trigger: "Phase 1, Week 22 long run"
  rule: "If any knee pain in weeks 19-22, peak long run (W23) caps at 20mi
         instead of 22mi."
  action: "Plan Adapter agent flags this on the W22 long-run review."

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
