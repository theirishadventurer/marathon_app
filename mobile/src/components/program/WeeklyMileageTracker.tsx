import { useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import type { CycleFull, WeekRollup } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { colors, radius } from '@/theme/tokens';

interface Props {
  cycles: CycleFull[];
  /** active cycle id chosen by upstream (defaults to first cycle whose
   *  start_date <= today <= end_date). */
  defaultCycleId: string | null;
  onWeekPress: (weekStartIso: string) => void;
}

const BAR_COLUMN_WIDTH = 22;
const CHART_HEIGHT = 120;

function maxPlanned(weeks: WeekRollup[]): number {
  return weeks.reduce((m, w) => Math.max(m, parseFloat(w.planned_mi)), 0);
}

function sumMi(weeks: WeekRollup[], key: 'planned_mi' | 'actual_mi'): number {
  return weeks.reduce((sum, w) => sum + parseFloat(w[key]), 0);
}

function deltaTone(deltaMi: number): { color: string; label: string } {
  if (deltaMi > 2) return { color: colors.accentCyan, label: '(ahead)' };
  if (deltaMi >= -2) return { color: colors.accentRun, label: '(on track)' };
  if (deltaMi >= -5) return { color: colors.accentStrength, label: '(slightly behind)' };
  return { color: colors.accentDanger, label: '(behind)' };
}

export function WeeklyMileageTracker({ cycles, defaultCycleId, onWeekPress }: Props) {
  const [activeCycleId, setActiveCycleId] = useState<string | null>(defaultCycleId);
  const activeCycle = useMemo<CycleFull | null>(
    () => cycles.find((c) => c.id === activeCycleId) ?? cycles[0] ?? null,
    [cycles, activeCycleId],
  );

  if (activeCycle === null) {
    return null;
  }

  const weeks = activeCycle.weeks;
  const peak = maxPlanned(weeks) || 1;
  const today = new Date();
  const todayIso = today.toISOString().slice(0, 10);

  const toDate = weeks.filter((w) => w.week_end <= todayIso || w.status === 'current');
  const plannedToDate = sumMi(toDate, 'planned_mi');
  const actualToDate = sumMi(toDate, 'actual_mi');
  const delta = actualToDate - plannedToDate;
  const tone = deltaTone(delta);

  const raceWord = activeCycle.race_name.split(' ')[0] ?? activeCycle.race_name;

  return (
    <RetroBorder>
      <View style={{ padding: 14 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
          <Text style={{
            fontFamily: 'VT323', fontSize: 18, color: colors.accentCyan, letterSpacing: 0.5,
          }}>
            ▸ Weekly mileage — {raceWord}
          </Text>
          <View style={{ flex: 1 }} />
          <View style={{ flexDirection: 'row' }}>
            {cycles.map((c) => {
              const selected = c.id === activeCycle.id;
              return (
                <Pressable
                  key={c.id}
                  onPress={() => { setActiveCycleId(c.id); }}
                  style={{
                    paddingHorizontal: 6,
                    paddingVertical: 2,
                    marginLeft: 4,
                    backgroundColor: selected ? colors.accentRun : colors.bgPanelAlt,
                    borderRadius: radius.sm,
                  }}
                >
                  <Text style={{
                    fontFamily: 'PressStart2P', fontSize: 8,
                    color: selected ? colors.bg : colors.ink, letterSpacing: 1,
                  }}>
                    P{c.sequence}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View style={{ flexDirection: 'row', marginBottom: 10 }}>
          <Text style={{ fontFamily: 'VT323', fontSize: 14, color: colors.inkDim }}>
            PLANNED <Text style={{ color: colors.ink }}>{Math.round(plannedToDate)}mi</Text>
          </Text>
          <Text style={{ fontFamily: 'VT323', fontSize: 14, color: colors.inkDim, marginLeft: 14 }}>
            ACTUAL <Text style={{ color: colors.ink }}>{actualToDate.toFixed(1)}mi</Text>
          </Text>
          <Text style={{ fontFamily: 'VT323', fontSize: 14, color: tone.color, marginLeft: 14 }}>
            DELTA {delta >= 0 ? '+' : ''}{delta.toFixed(1)}mi {tone.label}
          </Text>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: CHART_HEIGHT + 24 }}>
            {weeks.map((w) => {
              const planned = parseFloat(w.planned_mi);
              const actual = parseFloat(w.actual_mi);
              const plannedH = (planned / peak) * CHART_HEIGHT;
              const actualH = Math.min(actual, planned) / peak * CHART_HEIGHT;
              const fillColor =
                w.status === 'partial' || w.status === 'skipped' ? colors.accentDanger
                : w.status === 'current' ? colors.accentHi
                : colors.accentRun;
              return (
                <Pressable
                  key={w.week_number}
                  onPress={() => { onWeekPress(w.week_start); }}
                  style={{ width: BAR_COLUMN_WIDTH, alignItems: 'center' }}
                >
                  <View style={{ height: CHART_HEIGHT, justifyContent: 'flex-end' }}>
                    <View style={{
                      width: BAR_COLUMN_WIDTH - 6,
                      height: plannedH,
                      borderWidth: 1,
                      borderColor: colors.line,
                      backgroundColor: 'transparent',
                      position: 'absolute',
                      bottom: 0,
                    }} />
                    <View style={{
                      width: BAR_COLUMN_WIDTH - 8,
                      height: actualH,
                      backgroundColor: fillColor,
                      marginBottom: 0,
                      alignSelf: 'center',
                    }} />
                  </View>
                  <Text style={{
                    fontFamily: 'VT323', fontSize: 10, color: colors.inkMute, marginTop: 4,
                  }}>
                    W{w.week_number}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>
      </View>
    </RetroBorder>
  );
}
