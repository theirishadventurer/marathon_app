import { Text, View } from 'react-native';

import type { DayWorkouts, PlannedWorkoutOut } from '@/api/types';
import { WorkoutCard } from '@/components/WorkoutCard';
import { dayName, fromIso, toIso } from '@/lib/dates';
import { colors, fonts } from '@/theme/tokens';

interface Props {
  day: DayWorkouts;
  onWorkoutPress?: (w: PlannedWorkoutOut) => void;
  onWorkoutWhy?: (w: PlannedWorkoutOut) => void;
}

export function DayCard({ day, onWorkoutPress, onWorkoutWhy }: Props) {
  const date = fromIso(day.date);
  const isToday = day.date === toIso(new Date());
  const dayLabel = dayName(date, 'long');
  const dateLabel = `${date.getMonth() + 1}/${date.getDate()}`;

  return (
    <View className="mb-4">
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8, paddingHorizontal: 4 }}>
        {isToday && (
          <Text style={{ color: colors.accentRun, fontFamily: fonts.pixel, fontSize: 10, marginRight: 6 }}>▸</Text>
        )}
        <Text style={{
          color: isToday ? colors.accentRun : colors.ink,
          fontFamily: fonts.monoBold, fontSize: 14,
        }}>
          {dayLabel}
        </Text>
        <Text style={{ color: colors.inkDim, fontFamily: fonts.mono, fontSize: 12, marginLeft: 8 }}>
          {dateLabel}
        </Text>
      </View>

      {day.workouts.length === 0 ? (
        <View style={{
          backgroundColor: colors.bgPanelAlt,
          borderWidth: 2, borderColor: colors.line, padding: 14, alignItems: 'center',
        }}>
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkMute }}>Rest day</Text>
        </View>
      ) : (
        day.workouts.map((w) => (
          <WorkoutCard
            key={w.id}
            workout={w}
            compact
            onPress={onWorkoutPress !== undefined ? () => { onWorkoutPress(w); } : undefined}
            onWhy={onWorkoutWhy !== undefined ? () => { onWorkoutWhy(w); } : undefined}
          />
        ))
      )}
    </View>
  );
}
