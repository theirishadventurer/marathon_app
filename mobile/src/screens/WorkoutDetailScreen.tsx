import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Markdown from 'react-native-markdown-display';

import { useSkipWorkout, useWorkoutDetail } from '@/api/hooks/useWorkouts';
import type { CompletedWorkoutOut, PlannedWorkoutOut, ReconciliationOut } from '@/api/types';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { useEditFlow } from '@/hooks/useEditFlow';
import { fromIso, startOfWeek, toIso } from '@/lib/dates';
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
  body: { color: colors.ink, fontFamily: 'VT323', fontSize: 18, lineHeight: 22 },
  heading1: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 14, marginTop: 12, marginBottom: 8 },
  heading2: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 12, marginTop: 12, marginBottom: 6 },
  heading3: { color: colors.ink, fontFamily: 'PressStart2P', fontSize: 10, marginTop: 10, marginBottom: 4 },
  paragraph: { color: colors.ink, marginBottom: 8 },
  code_inline: { color: colors.accentHi, backgroundColor: colors.bgPanelAlt, paddingHorizontal: 4 },
  bullet_list: { marginBottom: 8 },
  list_item: { color: colors.ink },
  strong: { color: colors.ink, fontFamily: 'VT323', fontWeight: '700' as const },
  em: { color: colors.ink, fontStyle: 'italic' as const },
  hr: { backgroundColor: colors.line, height: 2, marginVertical: 12 },
};

function StatRow({ label, planned, actual }: { label: string; planned: string; actual: string }) {
  return (
    <View style={{
      flexDirection: 'row',
      paddingVertical: 8,
      borderBottomWidth: 2,
      borderBottomColor: colors.line,
    }}>
      <Text style={{ color: colors.inkDim, flex: 1.2, fontFamily: 'VT323', fontSize: 16 }}>{label}</Text>
      <Text style={{ color: colors.ink, flex: 1, fontFamily: 'VT323', fontSize: 18 }}>{planned}</Text>
      <Text style={{ color: colors.ink, flex: 1, fontFamily: 'VT323', fontSize: 18, fontWeight: '700' }}>{actual}</Text>
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
    <View style={{ marginTop: 20 }}>
      <Text style={{
        fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
      }}>
        PLANNED VS ACTUAL
      </Text>
      <View style={{ flexDirection: 'row', paddingBottom: 6, paddingTop: 8 }}>
        <Text style={{ color: colors.inkMute, flex: 1.2, fontFamily: 'PressStart2P', fontSize: 8 }}>METRIC</Text>
        <Text style={{ color: colors.inkMute, flex: 1, fontFamily: 'PressStart2P', fontSize: 8 }}>PLANNED</Text>
        <Text style={{ color: colors.inkMute, flex: 1, fontFamily: 'PressStart2P', fontSize: 8 }}>ACTUAL</Text>
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
      <StatRow
        label="Duration"
        planned={planned.duration_min !== null ? `${planned.duration_min}m` : '—'}
        actual={formatDuration(completed.duration_s)}
      />
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
    <View style={{ marginTop: 20 }}>
      <Text style={{
        fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
      }}>
        RECONCILIATION
      </Text>
      <RetroBorder>
        <View style={{ padding: 14 }}>
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1 }}>
            MATCH CONFIDENCE
          </Text>
          <Text style={{ fontFamily: 'VT323', fontSize: 22, color: colors.ink, marginBottom: 12 }}>
            {formatPercent(recon.match_confidence)}
          </Text>
          {recon.deviation_notes_md.trim().length > 0 && (
            <View>
              <Text style={{
                fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
              }}>
                DEVIATIONS
              </Text>
              <Markdown style={markdownStyle}>{recon.deviation_notes_md}</Markdown>
            </View>
          )}
          <View style={{ marginTop: 12 }}>
            <Text style={{
              fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
            }}>
              ANALYST REVIEW
            </Text>
            <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkMute, fontStyle: 'italic' }}>
              {recon.agent_review_md ?? 'Wired in session 3'}
            </Text>
          </View>
        </View>
      </RetroBorder>
    </View>
  );
}

export function WorkoutDetailScreen({ route, navigation }: Props) {
  const { workoutId } = route.params;
  const detail = useWorkoutDetail(workoutId);
  const skip = useSkipWorkout();
  const flow = useEditFlow();
  const weekStartIso = flow.editTarget !== null
    ? toIso(startOfWeek(fromIso(flow.editTarget.scheduled_date)))
    : null;

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

  const isSkipped = detail.data?.planned?.status === 'skipped';

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 12,
        borderBottomWidth: 2,
        borderBottomColor: colors.line,
        backgroundColor: colors.bgPanel,
      }}>
        <Pressable onPress={() => { navigation.goBack(); }} hitSlop={10}>
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 10, color: colors.accentRun, letterSpacing: 1,
          }}>
            ‹ BACK
          </Text>
        </Pressable>
        <View style={{ flex: 1 }} />
        {detail.data?.planned !== null && detail.data?.planned !== undefined && (
          <Pressable
            onPress={() => { flow.openEdit(detail.data!.planned!); }}
            hitSlop={10}
            style={{ marginLeft: 'auto' }}
          >
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 10, color: colors.accentRun, letterSpacing: 1 }}>
              EDIT
            </Text>
          </Pressable>
        )}
      </View>

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }}>
        {detail.isLoading && (
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
          }}>
            LOADING…
          </Text>
        )}
        {detail.isError && (
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentDanger, letterSpacing: 1,
          }}>
            COULD NOT LOAD WORKOUT
          </Text>
        )}
        {detail.data?.planned !== null && detail.data?.planned !== undefined && (
          <View>
            <Text style={{
              fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
            }}>
              WK {detail.data.planned.week_number} · {detail.data.planned.type.toUpperCase()}
            </Text>
            <Text style={{
              fontFamily: 'PressStart2P', fontSize: 14, color: colors.ink, letterSpacing: 1,
              marginTop: 6, marginBottom: 14,
            }}>
              {detail.data.planned.title.toUpperCase()}
            </Text>

            {detail.data.planned.description_md.trim().length > 0 && (
              <View>
                <Text style={{
                  fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
                }}>
                  PRESCRIPTION
                </Text>
                <Markdown style={markdownStyle}>{detail.data.planned.description_md}</Markdown>
              </View>
            )}

            {detail.data.planned.intent_md.trim().length > 0 && (
              <View style={{ marginTop: 16 }}>
                <Text style={{
                  fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 4,
                }}>
                  INTENT
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

      <View style={{
        paddingHorizontal: 20,
        paddingVertical: 12,
        borderTopWidth: 2,
        borderTopColor: colors.line,
        backgroundColor: colors.bgPanel,
      }}>
        <RetroButton
          tone="danger"
          label={isSkipped ? 'Skipped' : 'Skip workout'}
          onPress={onSkip}
          disabled={skip.isPending || isSkipped}
        />
      </View>

      <EditQuestSheet
        ref={flow.editRef}
        workout={flow.editTarget}
        submitting={flow.editPending}
        onConfirm={flow.confirmEdit}
        onClose={flow.closeEdit}
      />
      <DisplacedSheet
        ref={flow.displacedRef}
        snapshot={flow.displaced?.snapshot ?? null}
        weekStartIso={weekStartIso}
        submitting={flow.reschedulePending}
        onPick={flow.pickDisplacedDay}
        onDrop={flow.dropDisplaced}
        onClose={flow.dropDisplaced}
      />
      <ProposalSheet
        ref={flow.proposalRef}
        proposal={flow.proposal?.data ?? null}
        submitting={flow.applyPending}
        onApply={flow.applyProposal}
        onCancel={flow.cancelProposal}
      />
    </SafeAreaView>
  );
}
