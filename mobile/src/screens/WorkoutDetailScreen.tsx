import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Markdown from 'react-native-markdown-display';

import { useSkipWorkout, useWorkoutDetail } from '@/api/hooks/useWorkouts';
import type { CompletedWorkoutOut, PlannedWorkoutOut, ReconciliationOut } from '@/api/types';
import {
  formatDistance,
  formatDuration,
  formatPaceSPerKm,
  formatPercent,
  metersToMiles,
} from '@/lib/format';
import type { RootStackParamList } from '@/navigation/types';
import { colors } from '@/theme/tokens';

type Props = NativeStackScreenProps<RootStackParamList, 'WorkoutDetail'>;

const markdownStyle = {
  body: { color: colors.ink, fontSize: 15, lineHeight: 22 },
  heading1: { color: colors.ink, fontSize: 20, fontWeight: '700' as const, marginTop: 12, marginBottom: 8 },
  heading2: { color: colors.ink, fontSize: 17, fontWeight: '700' as const, marginTop: 12, marginBottom: 6 },
  heading3: { color: colors.ink, fontSize: 15, fontWeight: '700' as const, marginTop: 10, marginBottom: 4 },
  paragraph: { color: colors.ink, marginBottom: 8 },
  code_inline: { color: colors.accentRun, backgroundColor: colors.bgElev, paddingHorizontal: 4, borderRadius: 4 },
  bullet_list: { marginBottom: 8 },
  list_item: { color: colors.ink },
  strong: { color: colors.ink, fontWeight: '700' as const },
  em: { color: colors.ink, fontStyle: 'italic' as const },
};

function StatRow({ label, planned, actual }: { label: string; planned: string; actual: string }) {
  return (
    <View style={{ flexDirection: 'row', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
      <Text style={{ color: colors.inkDim, flex: 1.2, fontSize: 13 }}>{label}</Text>
      <Text style={{ color: colors.ink, flex: 1, fontSize: 14 }}>{planned}</Text>
      <Text style={{ color: colors.ink, flex: 1, fontSize: 14, fontWeight: '600' }}>{actual}</Text>
    </View>
  );
}

function ComparisonPanel({ planned, completed }: { planned: PlannedWorkoutOut; completed: CompletedWorkoutOut }) {
  const plannedMi = planned.distance_mi !== null ? formatDistance(parseFloat(planned.distance_mi)) : '—';
  const actualMi = (() => {
    const mi = metersToMiles(completed.distance_m);
    return mi !== null ? formatDistance(mi) : '—';
  })();
  return (
    <View style={{ marginTop: 16 }}>
      <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 8 }}>
        Planned vs actual
      </Text>
      <View style={{ flexDirection: 'row', paddingBottom: 6 }}>
        <Text style={{ color: colors.inkMute, flex: 1.2, fontSize: 11 }}>Metric</Text>
        <Text style={{ color: colors.inkMute, flex: 1, fontSize: 11 }}>Planned</Text>
        <Text style={{ color: colors.inkMute, flex: 1, fontSize: 11 }}>Actual</Text>
      </View>
      <StatRow label="Distance" planned={plannedMi} actual={actualMi} />
      <StatRow
        label="Pace"
        planned={planned.target_pace ?? '—'}
        actual={formatPaceSPerKm(completed.avg_pace_s_per_km)}
      />
      <StatRow
        label="Heart rate"
        planned={planned.target_hr_zone ?? '—'}
        actual={completed.avg_hr !== null ? `${completed.avg_hr} bpm avg` : '—'}
      />
      <StatRow label="Duration" planned={planned.duration_min !== null ? `${planned.duration_min}m` : '—'} actual={formatDuration(completed.duration_s)} />
      <StatRow
        label="Elevation"
        planned="—"
        actual={completed.elevation_gain_m !== null ? `${parseFloat(completed.elevation_gain_m).toFixed(0)} m` : '—'}
      />
    </View>
  );
}

function ReconciliationPanel({ recon }: { recon: ReconciliationOut }) {
  return (
    <View style={{ marginTop: 16 }}>
      <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 8 }}>
        Reconciliation
      </Text>
      <View style={{ backgroundColor: colors.bgCard, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: colors.line }}>
        <Text style={{ color: colors.inkDim, fontSize: 12 }}>Match confidence</Text>
        <Text style={{ color: colors.ink, fontSize: 16, fontWeight: '600', marginBottom: 12 }}>
          {formatPercent(recon.match_confidence)}
        </Text>
        {recon.deviation_notes_md.trim().length > 0 && (
          <View>
            <Text style={{ color: colors.inkDim, fontSize: 12, marginBottom: 4 }}>Deviations</Text>
            <Markdown style={markdownStyle}>{recon.deviation_notes_md}</Markdown>
          </View>
        )}
        <View style={{ marginTop: 12 }}>
          <Text style={{ color: colors.inkDim, fontSize: 12, marginBottom: 4 }}>Analyst review</Text>
          <Text style={{ color: colors.inkMute, fontStyle: 'italic' }}>
            {recon.agent_review_md ?? 'Wired in session 3'}
          </Text>
        </View>
      </View>
    </View>
  );
}

export function WorkoutDetailScreen({ route, navigation }: Props) {
  const { workoutId } = route.params;
  const detail = useWorkoutDetail(workoutId);
  const skip = useSkipWorkout();

  const onSkip = () => {
    Alert.alert(
      'Skip workout?',
      'It will be marked as skipped. You can move it instead from the Week view.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Skip',
          style: 'destructive',
          onPress: () => {
            skip.mutate(workoutId, {
              onSuccess: () => { navigation.goBack(); },
            });
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-row items-center px-5 py-3 border-b border-line">
        <Pressable onPress={() => { navigation.goBack(); }} hitSlop={10}>
          <Text className="text-accent-run text-base">‹ Back</Text>
        </Pressable>
        <View className="flex-1" />
      </View>

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }}>
        {detail.isLoading && (
          <Text className="text-ink-dim">Loading…</Text>
        )}
        {detail.isError && (
          <Text className="text-accent-danger">Could not load workout.</Text>
        )}
        {detail.data?.planned !== null && detail.data?.planned !== undefined && (
          <View>
            <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase' }}>
              Week {detail.data.planned.week_number} · {detail.data.planned.type}
            </Text>
            <Text style={{ color: colors.ink, fontSize: 24, fontWeight: '700', marginTop: 4, marginBottom: 14 }}>
              {detail.data.planned.title}
            </Text>

            {detail.data.planned.description_md.trim().length > 0 && (
              <View>
                <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 4 }}>
                  Prescription
                </Text>
                <Markdown style={markdownStyle}>{detail.data.planned.description_md}</Markdown>
              </View>
            )}

            {detail.data.planned.intent_md.trim().length > 0 && (
              <View style={{ marginTop: 16 }}>
                <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 4 }}>
                  Intent
                </Text>
                <Markdown style={markdownStyle}>{detail.data.planned.intent_md}</Markdown>
              </View>
            )}

            {detail.data.completed !== null && detail.data.completed !== undefined && (
              <ComparisonPanel planned={detail.data.planned} completed={detail.data.completed} />
            )}

            {detail.data.reconciliation !== null && detail.data.reconciliation !== undefined && (
              <ReconciliationPanel recon={detail.data.reconciliation} />
            )}
          </View>
        )}
      </ScrollView>

      <View className="px-5 py-3 border-t border-line">
        <Pressable
          onPress={onSkip}
          disabled={skip.isPending || detail.data?.planned?.status === 'skipped'}
          className="border border-line rounded-lg py-3 items-center"
        >
          <Text style={{ color: colors.accentDanger, fontWeight: '600' }}>
            {detail.data?.planned?.status === 'skipped' ? 'Skipped' : 'Skip workout'}
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
