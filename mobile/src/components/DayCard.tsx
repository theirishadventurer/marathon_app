import { Text, View } from 'react-native';

import type { DayWorkouts, PlannedWorkoutOut } from '@/api/types';
import { WorkoutCard } from '@/components/WorkoutCard';
import { dayName, fromIso, toIso } from '@/lib/dates';
import { colors } from '@/theme/tokens';

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
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6, paddingHorizontal: 4 }}>
        {isToday && (
          <Text style={{ color: colors.accentRun, fontFamily: 'PressStart2P', fontSize: 10, marginRight: 6 }}>▸</Text>
        )}
        <Text style={{
          color: isToday ? colors.accentRun : colors.ink,
          fontFamily: 'PressStart2P', fontSize: 10, letterSpacing: 1,
        }}>
          {dayLabel.toUpperCase()}
        </Text>
        <Text style={{ color: colors.inkDim, fontFamily: 'VT323', fontSize: 14, marginLeft: 8 }}>
          {dateLabel}
        </Text>
      </View>

      {day.workouts.length === 0 ? (
        <View style={{
          backgroundColor: colors.bgPanelAlt,
          borderWidth: 2, borderColor: colors.line, padding: 14, alignItems: 'center',
        }}>
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkMute, letterSpacing: 1 }}>REST</Text>
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
