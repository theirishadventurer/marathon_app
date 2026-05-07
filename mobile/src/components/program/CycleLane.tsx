import { useEffect, useRef } from 'react';
import { ScrollView, Text, View } from 'react-native';

import type { CycleFull, WeekRollup } from '@/api/types';
import { RaceMilestoneTile } from '@/components/program/RaceMilestoneTile';
import { WeekTile } from '@/components/program/WeekTile';
import { colors, fonts } from '@/theme/tokens';

interface Props {
  cycle: CycleFull;
  onWeekPress: (weekStartIso: string) => void;
  onRacePress: (workoutId: string) => void;
}

export function CycleLane({ cycle, onWeekPress, onRacePress }: Props) {
  const scrollRef = useRef<ScrollView>(null);
  const currentIdx = cycle.weeks.findIndex((w) => w.status === 'current');

  useEffect(() => {
    if (currentIdx < 0) return;
    const offset = Math.max(0, currentIdx * 56 - 80);
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ y: offset, animated: false });
    });
  }, [currentIdx]);

  return (
    <View style={{ flex: 1, marginHorizontal: 4 }}>
      <View style={{ marginBottom: 8 }}>
        <Text style={{
          fontFamily: fonts.monoBold, fontSize: 14, color: colors.ink,
        }}>
          P{cycle.sequence} {(cycle.race_name.split(' ')[0] ?? cycle.race_name).toUpperCase()}
        </Text>
        <Text style={{
          fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginTop: 2,
        }}>
          {cycle.weeks.length} weeks
        </Text>
      </View>
      <ScrollView
        ref={scrollRef}
        showsVerticalScrollIndicator={false}
        nestedScrollEnabled
      >
        {cycle.weeks.map((w: WeekRollup) => (
          <WeekTile
            key={`${cycle.id}-${w.week_number}`}
            week={w}
            onPress={() => { onWeekPress(w.week_start); }}
          />
        ))}
        {cycle.race_planned_id !== null && (
          <RaceMilestoneTile
            raceName={cycle.race_name}
            raceDate={cycle.race_date}
            onPress={() => {
              if (cycle.race_planned_id !== null) onRacePress(cycle.race_planned_id);
            }}
          />
        )}
      </ScrollView>
    </View>
  );
}
