import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanToday, usePlanWeek } from '@/api/hooks/usePlan';
import { useRecentCompleted } from '@/api/hooks/useRecentCompleted';
import { useSync } from '@/api/hooks/useSync';
import type { CompletedWorkoutOut, PlannedWorkoutOut } from '@/api/types';
import { BrandBanner } from '@/components/BrandBanner';
import { DayToggle } from '@/components/DayToggle';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RecentRunSheet } from '@/components/RecentRunSheet';
import { RecentRunsStrip } from '@/components/RecentRunsStrip';
import { SectionHeader } from '@/components/SectionHeader';
import { WhySheet } from '@/components/WhySheet';
import { WorkoutCard } from '@/components/WorkoutCard';
import { useEditFlow } from '@/hooks/useEditFlow';
import { addDays, fromIso, startOfWeek, toIso } from '@/lib/dates';
import type { RootStackParamList } from '@/navigation/types';
import { colors, fonts } from '@/theme/tokens';

type DayChoice = 'TODAY' | 'TOMORROW';
const DAY_OPTIONS: readonly DayChoice[] = ['TODAY', 'TOMORROW'];

export function TodayScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const today = usePlanToday();
  const plan = usePlanCurrent();
  const recent = useRecentCompleted(5);
  const sync = useSync();
  const todayIsoStr = useMemo(() => toIso(new Date()), []);
  const tomorrowIsoStr = useMemo(() => toIso(addDays(new Date(), 1)), []);
  const week = usePlanWeek(todayIsoStr);
  const [dayChoice, setDayChoice] = useState<DayChoice>('TODAY');

  const sheetRef = useRef<BottomSheet>(null);
  const recentSheetRef = useRef<BottomSheet>(null);
  const [whyWorkout] = useState<PlannedWorkoutOut | null>(null);
  const [recentSelected, setRecentSelected] = useState<CompletedWorkoutOut | null>(null);
  const flow = useEditFlow();
  const weekStartIso = flow.editTarget !== null
    ? toIso(startOfWeek(fromIso(flow.editTarget.scheduled_date)))
    : null;

  const tomorrowWorkouts = useMemo<PlannedWorkoutOut[]>(() => {
    if (week.data === undefined) return [];
    const day = week.data.days.find((d) => d.date === tomorrowIsoStr);
    return day?.workouts ?? [];
  }, [week.data, tomorrowIsoStr]);

  const shownWorkouts = dayChoice === 'TODAY'
    ? (today.data?.workouts ?? [])
    : tomorrowWorkouts;

  const sectionLabel = dayChoice === 'TODAY' ? "Today's session" : "Tomorrow's session";

  const isLoading = dayChoice === 'TODAY' ? today.isLoading : week.isLoading;
  const isError = dayChoice === 'TODAY' ? today.isError : week.isError;

  const subhead = useMemo(() => {
    const planName = plan.data?.plan_name ?? 'MARATHON_TRILOGY';
    const cycle = plan.data?.cycle_progress;
    const race = plan.data?.active_cycle?.race_name ?? '';
    const raceShort = race.length > 0 ? ` · ${race} ${cycle?.days_to_race ?? '—'}d` : '';
    if (cycle === null || cycle === undefined) return planName.toUpperCase();
    return `${planName.toUpperCase()} — WK ${cycle.week} / ${cycle.total_weeks}${raceShort}`;
  }, [plan.data]);

  const onRefresh = useCallback(async () => {
    await Promise.all([today.refetch(), plan.refetch(), recent.refetch(), week.refetch()]);
  }, [today, plan, recent, week]);

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

  const closeWhy = () => { sheetRef.current?.close(); };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={today.isFetching || plan.isFetching || recent.isFetching || week.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor={colors.inkDim}
          />
        }
      >
        <BrandBanner subhead={subhead} />

        <View style={{ paddingHorizontal: 20, paddingTop: 4 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 18 }}>
            <View style={{ flex: 1 }}>
              <DayToggle<DayChoice>
                options={DAY_OPTIONS}
                value={dayChoice}
                onChange={setDayChoice}
              />
            </View>
            <Pressable
              onPress={onSync}
              disabled={sync.isPending}
              hitSlop={8}
              style={{
                width: 36, height: 36, borderRadius: 18,
                borderWidth: 1, borderColor: colors.line,
                alignItems: 'center', justifyContent: 'center',
                opacity: sync.isPending ? 0.4 : 1,
              }}
            >
              <Text style={{ fontFamily: fonts.mono, fontSize: 16, color: colors.accentCyan }}>
                {sync.isPending ? '…' : '↻'}
              </Text>
            </Pressable>
          </View>

          <SectionHeader label={sectionLabel} />

          {isLoading ? (
            <View style={{ alignItems: 'center', paddingVertical: 40 }}>
              <ActivityIndicator color={colors.accentRun} />
            </View>
          ) : isError ? (
            <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, letterSpacing: 0.5 }}>
              Could not load.
            </Text>
          ) : shownWorkouts.length === 0 ? (
            <View style={{
              backgroundColor: colors.bgPanelAlt, borderWidth: 1, borderColor: colors.line,
              borderRadius: 6, padding: 18, alignItems: 'center',
            }}>
              <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, letterSpacing: 0.5 }}>
                Rest day — no work scheduled.
              </Text>
            </View>
          ) : (
            shownWorkouts.map((w) => (
              <WorkoutCard
                key={w.id}
                workout={w}
                onPress={() => { openDetail(w); }}
              />
            ))
          )}

          {today.data?.coach_brief !== null && today.data?.coach_brief !== undefined && (
            <View>
              <SectionHeader label="Coach brief" />
              <Text style={{
                fontFamily: fonts.mono, fontSize: 14, color: colors.ink, lineHeight: 22,
              }}>
                {today.data.coach_brief}
              </Text>
            </View>
          )}

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
        </View>
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
