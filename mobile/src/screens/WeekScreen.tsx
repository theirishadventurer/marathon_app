import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanWeek } from '@/api/hooks/usePlan';
import type { PlannedWorkoutOut } from '@/api/types';
import { DraggableWeekList } from '@/components/DraggableWeekList';
import { ProposalSheet } from '@/components/ProposalSheet';
import { WhySheet } from '@/components/WhySheet';
import { useDragMove } from '@/hooks/useDragMove';
import { addDays, fromIso, toIso } from '@/lib/dates';
import type { RootStackParamList } from '@/navigation/types';

function formatWeekLabel(weekStartIso: string): string {
  const start = fromIso(weekStartIso);
  const end = addDays(start, 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${fmt(start)} – ${fmt(end)}`;
}

export function WeekScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const [cursorIso, setCursorIso] = useState<string>(toIso(new Date()));
  const week = usePlanWeek(cursorIso);
  const plan = usePlanCurrent();
  const drag = useDragMove();

  const whySheetRef = useRef<BottomSheet>(null);
  const proposalSheetRef = useRef<BottomSheet>(null);
  const [whyWorkout, setWhyWorkout] = useState<PlannedWorkoutOut | null>(null);

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
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <View className="px-5 pt-4 pb-3 border-b border-line">
        <View className="flex-row items-center justify-between">
          <Pressable onPress={goPrev} hitSlop={10} className="px-2 py-1">
            <Text className="text-ink text-xl">‹</Text>
          </Pressable>
          <View className="items-center">
            <Text className="text-ink text-base font-semibold">{weekLabel}</Text>
            {plan.data?.cycle_progress !== null && plan.data?.cycle_progress !== undefined && (
              <Text className="text-ink-dim text-xs">
                Week {plan.data.cycle_progress.week} / {plan.data.cycle_progress.total_weeks}
              </Text>
            )}
          </View>
          <Pressable onPress={goNext} hitSlop={10} className="px-2 py-1">
            <Text className="text-ink text-xl">›</Text>
          </Pressable>
        </View>
        <Pressable
          onPress={jumpToday}
          hitSlop={6}
          className="self-center mt-2"
        >
          <Text className="text-accent-run text-xs uppercase">Jump to today</Text>
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={week.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor="#a1a1aa"
          />
        }
      >
        {week.isLoading && (
          <View className="items-center py-10">
            <ActivityIndicator color="#34d399" />
          </View>
        )}
        {week.isError && (
          <Text className="text-accent-danger">Could not load this week.</Text>
        )}
        {week.data !== undefined && (
          <DraggableWeekList
            week={week.data}
            onWorkoutPress={openDetail}
            onWorkoutWhy={openWhy}
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
    </SafeAreaView>
  );
}
