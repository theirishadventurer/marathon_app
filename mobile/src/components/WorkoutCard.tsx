import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutOut } from '@/api/types';
import { formatDistance } from '@/lib/format';
import { colors, familyColor, type WorkoutFamily } from '@/theme/tokens';

const FAMILIES: ReadonlySet<WorkoutFamily> = new Set(['running', 'strength', 'other']);

function asFamily(raw: string): WorkoutFamily {
  return FAMILIES.has(raw as WorkoutFamily) ? (raw as WorkoutFamily) : 'other';
}

const STATUS_LABEL: Record<string, string> = {
  planned: 'Planned',
  moved: 'Moved',
  skipped: 'Skipped',
  done: 'Done',
};

const STATUS_COLOR: Record<string, string> = {
  planned: colors.inkDim,
  moved: colors.accentRest,
  skipped: colors.accentDanger,
  done: colors.accentRun,
};

interface Props {
  workout: PlannedWorkoutOut;
  onPress?: () => void;
  onWhy?: () => void;
  compact?: boolean;
}

export function WorkoutCard({ workout, onPress, onWhy, compact = false }: Props) {
  const family = asFamily(workout.family);
  const tint = familyColor[family];
  const distance = workout.distance_mi !== null ? formatDistance(parseFloat(workout.distance_mi)) : null;
  const statusLabel = STATUS_LABEL[workout.status] ?? workout.status;
  const statusColor = STATUS_COLOR[workout.status] ?? colors.inkDim;

  return (
    <Pressable
      onPress={onPress}
      className="bg-bg-card rounded-xl px-4 py-3 mb-3 border border-line"
    >
      <View className="flex-row items-center mb-2">
        <View
          style={{ backgroundColor: tint, width: 8, height: 8, borderRadius: 4 }}
          className="mr-2"
        />
        <Text className="text-ink-dim text-xs uppercase tracking-wide">
          {workout.type}
        </Text>
        <View className="flex-1" />
        <Text style={{ color: statusColor }} className="text-xs uppercase">
          {statusLabel}
        </Text>
      </View>

      <Text className="text-ink text-lg font-semibold mb-1" numberOfLines={2}>
        {workout.title}
      </Text>

      {!compact && (
        <View className="flex-row items-center flex-wrap mt-1">
          {distance !== null && (
            <Text className="text-ink-dim text-sm mr-3">{distance}</Text>
          )}
          {workout.duration_min !== null && (
            <Text className="text-ink-dim text-sm mr-3">{workout.duration_min}min</Text>
          )}
          {workout.target_pace !== null && (
            <Text className="text-ink-dim text-sm mr-3">{workout.target_pace}</Text>
          )}
          {workout.target_hr_zone !== null && (
            <Text className="text-ink-dim text-sm">{workout.target_hr_zone}</Text>
          )}
        </View>
      )}

      {onWhy !== undefined && (
        <View className="flex-row mt-3">
          <Pressable
            onPress={onWhy}
            hitSlop={8}
            className="border border-line rounded-md px-3 py-1"
          >
            <Text className="text-ink-dim text-xs">Why?</Text>
          </Pressable>
        </View>
      )}
    </Pressable>
  );
}
