import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanWeek } from '@/api/hooks/usePlan';
import type { PlannedWorkoutOut } from '@/api/types';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { DraggableWeekList } from '@/components/DraggableWeekList';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { WhySheet } from '@/components/WhySheet';
import { useDragMove } from '@/hooks/useDragMove';
import { useEditFlow } from '@/hooks/useEditFlow';
import { addDays, fromIso, startOfWeek, toIso } from '@/lib/dates';
import type { RootStackParamList, TabParamList } from '@/navigation/types';
import { colors } from '@/theme/tokens';

function formatWeekLabel(weekStartIso: string): string {
  const start = fromIso(weekStartIso);
  const end = addDays(start, 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${fmt(start)} – ${fmt(end)}`;
}

export function WeekScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const route = useRoute<RouteProp<TabParamList, 'Week'>>();
  const initialDate = route.params?.initialDate;
  const [cursorIso, setCursorIso] = useState<string>(initialDate ?? toIso(new Date()));
  const week = usePlanWeek(cursorIso);
  const plan = usePlanCurrent();
  const drag = useDragMove();
  const flow = useEditFlow();

  const whySheetRef = useRef<BottomSheet>(null);
  const proposalSheetRef = useRef<BottomSheet>(null);
  const [whyWorkout, setWhyWorkout] = useState<PlannedWorkoutOut | null>(null);

  const weekStartIso = flow.editTarget !== null
    ? toIso(startOfWeek(fromIso(flow.editTarget.scheduled_date)))
    : null;

  // Open proposal sheet when a proposal lands or when we are awaiting one.
  useEffect(() => {
    if (drag.pending !== null || drag.proposal !== null) {
      proposalSheetRef.current?.snapToIndex(0);
    } else {
      proposalSheetRef.current?.close();
    }
  }, [drag.pending, drag.proposal]);

  const onRefresh = useCallback(async () => {
    await Promise.all([week.refetch(), plan.refetch()]);
  }, [week, plan]);

  const goPrev = () => {
    setCursorIso((prev) => toIso(addDays(fromIso(prev), -7)));
  };
  const goNext = () => {
    setCursorIso((prev) => toIso(addDays(fromIso(prev), 7)));
  };
  const jumpToday = () => {
    setCursorIso(toIso(new Date()));
  };

  const openWhy = (w: PlannedWorkoutOut) => {
    setWhyWorkout(w);
    whySheetRef.current?.snapToIndex(0);
  };
  const closeWhy = () => {
    whySheetRef.current?.close();
  };
  const openDetail = (w: PlannedWorkoutOut) => {
    navigation.navigate('WorkoutDetail', { workoutId: w.id });
  };
  const requestMove = (w: PlannedWorkoutOut, newDate: string) => {
    void drag.requestMove(w, newDate).catch(() => {
      // surface error UX later; mutation already rolls back optimistic state
    });
  };

  const weekLabel = useMemo(
    () => (week.data !== undefined ? formatWeekLabel(week.data.week_start) : ''),
    [week.data],
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <View style={{
        paddingHorizontal: 20,
        paddingTop: 16,
        paddingBottom: 12,
        borderBottomWidth: 2,
        borderBottomColor: colors.line,
        backgroundColor: colors.bgPanel,
      }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Pressable onPress={goPrev} hitSlop={10} style={{ paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 16, color: colors.ink }}>‹</Text>
          </Pressable>
          <View style={{ alignItems: 'center' }}>
            <Text style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink }}>{weekLabel}</Text>
            {plan.data?.cycle_progress !== null && plan.data?.cycle_progress !== undefined && (
              <Text style={{
                fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1, marginTop: 4,
              }}>
                WK {plan.data.cycle_progress.week} / {plan.data.cycle_progress.total_weeks}
              </Text>
            )}
          </View>
          <Pressable onPress={goNext} hitSlop={10} style={{ paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ fontFamily: 'PressStart2P', fontSize: 16, color: colors.ink }}>›</Text>
          </Pressable>
        </View>
        <Pressable
          onPress={jumpToday}
          hitSlop={6}
          style={{ alignSelf: 'center', marginTop: 8 }}
        >
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentRun, letterSpacing: 1,
          }}>
            ▸ JUMP TO TODAY
          </Text>
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={week.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor={colors.inkDim}
          />
        }
      >
        {week.isLoading && (
          <View style={{ alignItems: 'center', paddingVertical: 40 }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        )}
        {week.isError && (
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentDanger, letterSpacing: 1,
          }}>
            COULD NOT LOAD WEEK
          </Text>
        )}
        {week.data !== undefined && (
          <DraggableWeekList
            week={week.data}
            onWorkoutPress={openDetail}
            onWorkoutWhy={openWhy}
            onWorkoutEdit={flow.openEdit}
            onMoveRequest={requestMove}
            disabled={drag.pending !== null}
          />
        )}
      </ScrollView>

      <WhySheet ref={whySheetRef} workout={whyWorkout} onClose={closeWhy} />
      <ProposalSheet
        ref={proposalSheetRef}
        proposal={drag.proposal}
        submitting={drag.submitting}
        onApply={drag.apply}
        onCancel={drag.cancel}
      />
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
