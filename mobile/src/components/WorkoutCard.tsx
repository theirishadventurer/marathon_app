import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroPill } from '@/components/retro/RetroPill';
import { formatDistance } from '@/lib/format';
import { colors, familyColor, type WorkoutFamily } from '@/theme/tokens';

const FAMILIES: ReadonlySet<WorkoutFamily> = new Set(['running', 'strength', 'other']);

function asFamily(raw: string): WorkoutFamily {
  return FAMILIES.has(raw as WorkoutFamily) ? (raw as WorkoutFamily) : 'other';
}

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
  onEdit?: () => void;
  compact?: boolean;
}

export function WorkoutCard({ workout, onPress, onWhy, onEdit, compact = false }: Props) {
  const family = asFamily(workout.family);
  const tint = familyColor[family];
  const distance = workout.distance_mi !== null
    ? formatDistance(parseFloat(workout.distance_mi))
    : null;
  const statusColor = STATUS_COLOR[workout.status] ?? colors.inkDim;
  const wasOriginal = workout.original_snapshot;

  return (
    <Pressable onPress={onPress} style={{ marginBottom: 14 }}>
      <RetroBorder>
        <View style={{ padding: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
            <View style={{
              backgroundColor: tint, width: 10, height: 10, marginRight: 8,
            }} />
            <Text style={{
              fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
            }}>
              {workout.type.toUpperCase()}
            </Text>
            <View style={{ flex: 1 }} />
            <RetroPill label={workout.status} color={statusColor} />
          </View>

          <Text style={{
            fontFamily: 'VT323', fontSize: 22, color: colors.ink, lineHeight: 24,
          }} numberOfLines={2}>
            {workout.title}
          </Text>

          {wasOriginal !== null && (
            <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}>
              <Text style={{
                fontFamily: 'VT323', fontSize: 14, color: colors.inkDim,
              }}>
                ↻ was: {wasOriginal.title}
              </Text>
            </View>
          )}

          {!compact && (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 }}>
              {distance !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {distance}
                </Text>
              )}
              {workout.duration_min !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {workout.duration_min}min
                </Text>
              )}
              {workout.target_pace !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginRight: 12 }}>
                  {workout.target_pace}
                </Text>
              )}
              {workout.target_hr_zone !== null && (
                <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim }}>
                  {workout.target_hr_zone}
                </Text>
              )}
            </View>
          )}

          {(onWhy !== undefined || onEdit !== undefined) && (
            <View style={{ flexDirection: 'row', marginTop: 10, gap: 8 }}>
              {onWhy !== undefined && (
                <Pressable
                  onPress={onWhy}
                  hitSlop={8}
                  style={{ borderColor: colors.line, borderWidth: 2, paddingHorizontal: 8, paddingVertical: 4 }}
                >
                  <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink }}>WHY?</Text>
                </Pressable>
              )}
              {onEdit !== undefined && (
                <Pressable
                  onPress={onEdit}
                  hitSlop={8}
                  style={{ borderColor: colors.line, borderWidth: 2, paddingHorizontal: 8, paddingVertical: 4 }}
                >
                  <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink }}>EDIT</Text>
                </Pressable>
              )}
            </View>
          )}
        </View>
      </RetroBorder>
    </Pressable>
  );
}
