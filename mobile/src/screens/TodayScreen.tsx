import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanToday } from '@/api/hooks/usePlan';
import { useRecentCompleted } from '@/api/hooks/useRecentCompleted';
import { useSync } from '@/api/hooks/useSync';
import type { CompletedWorkoutOut, PlannedWorkoutOut } from '@/api/types';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RecentRunSheet } from '@/components/RecentRunSheet';
import { RecentRunsStrip } from '@/components/RecentRunsStrip';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { SectionHeader } from '@/components/SectionHeader';
import { WorkoutCard } from '@/components/WorkoutCard';
import { WhySheet } from '@/components/WhySheet';
import { useEditFlow } from '@/hooks/useEditFlow';
import { fromIso, startOfWeek, toIso } from '@/lib/dates';
import type { RootStackParamList } from '@/navigation/types';
import { colors, fonts, radius } from '@/theme/tokens';

function formatHeaderDate(iso: string): string {
  const d = fromIso(iso);
  return `▸ TODAY  ${d.getMonth() + 1}/${d.getDate()}`;
}

export function TodayScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const today = usePlanToday();
  const plan = usePlanCurrent();
  const recent = useRecentCompleted(5);
  const sync = useSync();
  const sheetRef = useRef<BottomSheet>(null);
  const recentSheetRef = useRef<BottomSheet>(null);
  const [whyWorkout, setWhyWorkout] = useState<PlannedWorkoutOut | null>(null);
  const [recentSelected, setRecentSelected] = useState<CompletedWorkoutOut | null>(null);
  const flow = useEditFlow();
  const weekStartIso = flow.editTarget !== null
    ? toIso(startOfWeek(fromIso(flow.editTarget.scheduled_date)))
    : null;

  const onRefresh = useCallback(async () => {
    await Promise.all([today.refetch(), plan.refetch(), recent.refetch()]);
  }, [today, plan, recent]);

  const openWhy = (w: PlannedWorkoutOut) => {
    setWhyWorkout(w);
    sheetRef.current?.snapToIndex(0);
  };
  const closeWhy = () => {
    sheetRef.current?.close();
  };
  const openDetail = (w: PlannedWorkoutOut) => {
    navigation.navigate('WorkoutDetail', { workoutId: w.id });
  };

  const onSync = () => {
    sync.mutate(undefined, {
      onSuccess: (report) => {
        Alert.alert(
          'Sync complete',
          `${report.synced_activities} activities, ${report.synced_metrics} metrics${report.errors.length > 0 ? ` (${report.errors.length} errors)` : ''}`,
        );
      },
      onError: (err) => {
        Alert.alert('Sync failed', err.message ?? 'Unknown error');
      },
    });
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={today.isFetching || plan.isFetching || recent.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor={colors.inkDim}
          />
        }
      >
        <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, letterSpacing: 0.5 }}>
          {today.data !== undefined ? formatHeaderDate(today.data.date) : '▸ TODAY'}
        </Text>
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 22, color: colors.ink, marginTop: 6 }}>
          What&apos;s on tap
        </Text>
        {plan.data?.cycle_progress !== null && plan.data?.cycle_progress !== undefined && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginTop: 4 }}>
            Week {plan.data.cycle_progress.week} of {plan.data.cycle_progress.total_weeks} ·{' '}
            {plan.data.cycle_progress.days_to_race} days to {plan.data.active_cycle?.race_name ?? 'race'}
          </Text>
        )}

        <Pressable
          onPress={onSync}
          hitSlop={8}
          disabled={sync.isPending}
          style={{
            backgroundColor: colors.accentCyan,
            borderRadius: radius.sm,
            paddingHorizontal: 8,
            paddingVertical: 4,
            alignSelf: 'flex-start',
            marginTop: 8,
            marginBottom: 14,
            opacity: sync.isPending ? 0.4 : 1,
          }}
        >
          <Text style={{ fontFamily: fonts.pixel, fontSize: 8, color: colors.bg, letterSpacing: 1 }}>
            {sync.isPending ? 'SYNCING…' : 'SYNC'}
          </Text>
        </Pressable>

        {today.data?.coach_brief !== null && today.data?.coach_brief !== undefined && (
          <RetroBorder style={{ marginVertical: 14 }}>
            <View style={{ padding: 14 }}>
              <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.accentCyan, letterSpacing: 0.5, marginBottom: 6 }}>
                ▸ COACH BRIEF
              </Text>
              <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.ink, lineHeight: 20 }}>
                {today.data.coach_brief}
              </Text>
            </View>
          </RetroBorder>
        )}

        {today.isLoading && (
          <View style={{ alignItems: 'center', paddingVertical: 40 }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        )}

        {today.isError && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, letterSpacing: 0.5 }}>
            Could not load today.
          </Text>
        )}

        {today.data !== undefined && today.data.workouts.length === 0 && !today.isLoading && (
          <RetroBorder>
            <View style={{ padding: 20, alignItems: 'center' }}>
              <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, letterSpacing: 0.5 }}>
                Rest day — no work scheduled.
              </Text>
            </View>
          </RetroBorder>
        )}

        {today.data?.workouts.map((w) => (
          <WorkoutCard
            key={w.id}
            workout={w}
            onPress={() => { openDetail(w); }}
            onWhy={() => { openWhy(w); }}
            onEdit={() => { flow.openEdit(w); }}
          />
        ))}

        <SectionHeader label="Recent runs" />
        {recent.isLoading ? (
          <ActivityIndicator color={colors.accentRun} />
        ) : recent.isError ? (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger }}>
            Could not load recent runs.
          </Text>
        ) : (
          <RecentRunsStrip
            runs={recent.data ?? []}
            onPress={(r) => {
              setRecentSelected(r);
              recentSheetRef.current?.snapToIndex(0);
            }}
          />
        )}
      </ScrollView>

      <WhySheet ref={sheetRef} workout={whyWorkout} onClose={closeWhy} />
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
      <RecentRunSheet
        ref={recentSheetRef}
        run={recentSelected}
        onClose={() => recentSheetRef.current?.close()}
      />
    </SafeAreaView>
  );
}
