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
      <View className="flex-row items-baseline mb-2 px-1">
        <Text
          style={{ color: isToday ? colors.accentRun : colors.ink }}
          className="text-base font-semibold"
        >
          {dayLabel}
        </Text>
        <Text className="text-ink-dim text-xs ml-2">{dateLabel}</Text>
        {isToday && (
          <Text className="text-accent-run text-[10px] uppercase ml-2">Today</Text>
        )}
      </View>

      {day.workouts.length === 0 ? (
        <View className="bg-bg-card rounded-xl p-4 border border-line items-center">
          <Text className="text-ink-mute text-sm">Rest</Text>
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
