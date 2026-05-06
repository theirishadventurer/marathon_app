import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanToday } from '@/api/hooks/usePlan';
import type { PlannedWorkoutOut } from '@/api/types';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { WorkoutCard } from '@/components/WorkoutCard';
import { WhySheet } from '@/components/WhySheet';
import { useEditFlow } from '@/hooks/useEditFlow';
import { fromIso, startOfWeek, toIso } from '@/lib/dates';
import type { RootStackParamList } from '@/navigation/types';
import { colors } from '@/theme/tokens';

function formatHeaderDate(iso: string): string {
  const d = fromIso(iso);
  return `▸ TODAY  ${d.getMonth() + 1}/${d.getDate()}`;
}

export function TodayScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const today = usePlanToday();
  const plan = usePlanCurrent();
  const sheetRef = useRef<BottomSheet>(null);
  const [whyWorkout, setWhyWorkout] = useState<PlannedWorkoutOut | null>(null);
  const flow = useEditFlow();
  const weekStartIso = flow.editTarget !== null
    ? toIso(startOfWeek(fromIso(flow.editTarget.scheduled_date)))
    : null;

  const onRefresh = useCallback(async () => {
    await Promise.all([today.refetch(), plan.refetch()]);
  }, [today, plan]);

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

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={today.isFetching || plan.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor={colors.inkDim}
          />
        }
      >
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1 }}>
          {today.data !== undefined ? formatHeaderDate(today.data.date) : '▸ TODAY'}
        </Text>
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 14, color: colors.ink, letterSpacing: 1, marginTop: 6 }}>
          WHAT&apos;S ON TAP
        </Text>
        {plan.data?.cycle_progress !== null && plan.data?.cycle_progress !== undefined && (
          <Text style={{ fontFamily: 'VT323', fontSize: 14, color: colors.inkDim, marginTop: 4, marginBottom: 16 }}>
            Week {plan.data.cycle_progress.week} of {plan.data.cycle_progress.total_weeks} ·{' '}
            {plan.data.cycle_progress.days_to_race} days to {plan.data.active_cycle?.race_name ?? 'race'}
          </Text>
        )}

        <RetroBorder style={{ marginBottom: 24 }}>
          <View style={{ padding: 14 }}>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginBottom: 6 }}>
              COACH BRIEF
            </Text>
            <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, fontStyle: 'italic' }}>
              Coach brief — wired in session 3
            </Text>
          </View>
        </RetroBorder>

        {today.isLoading && (
          <View style={{ alignItems: 'center', paddingVertical: 40 }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        )}

        {today.isError && (
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentDanger, letterSpacing: 1 }}>
            COULD NOT LOAD TODAY
          </Text>
        )}

        {today.data !== undefined && today.data.workouts.length === 0 && !today.isLoading && (
          <RetroBorder>
            <View style={{ padding: 20, alignItems: 'center' }}>
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1 }}>
                REST DAY — NO WORK SCHEDULED
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

        <Text style={{
          fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
          marginTop: 32, marginBottom: 12,
        }}>
          RECENT QUESTS
        </Text>
        <RetroBorder>
          <View style={{ padding: 14 }}>
            <Text style={{ fontFamily: 'VT323', fontSize: 14, color: colors.inkDim }}>
              Recent runs strip lands once `/workouts/completed/recent` ships.
            </Text>
          </View>
        </RetroBorder>
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
    </SafeAreaView>
  );
}
