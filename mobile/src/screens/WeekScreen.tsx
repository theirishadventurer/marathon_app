import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanWeek } from '@/api/hooks/usePlan';
import type { PlannedWorkoutOut } from '@/api/types';
import { BrandBanner } from '@/components/BrandBanner';
import { DayToggle } from '@/components/DayToggle';
import { DisplacedSheet } from '@/components/DisplacedSheet';
import { DraggableWeekList } from '@/components/DraggableWeekList';
import { EditQuestSheet } from '@/components/EditQuestSheet';
import { ProposalSheet } from '@/components/ProposalSheet';
import { useDragMove } from '@/hooks/useDragMove';
import { useEditFlow } from '@/hooks/useEditFlow';
import { addDays, dayName, fromIso, startOfWeek, toIso } from '@/lib/dates';
import type { RootStackParamList, TabParamList } from '@/navigation/types';
import { colors, fonts } from '@/theme/tokens';

type DayCode = 'MON' | 'TUE' | 'WED' | 'THU' | 'FRI' | 'SAT' | 'SUN';
const DAY_CODES: readonly DayCode[] = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

function isoToDayCode(iso: string): DayCode {
  const d = fromIso(iso);
  return dayName(d, 'short').toUpperCase() as DayCode;
}

function formatRange(weekStartIso: string): string {
  const start = fromIso(weekStartIso);
  const end = addDays(start, 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase();
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

  const proposalSheetRef = useRef<BottomSheet>(null);
  const scrollRef = useRef<ScrollView>(null);
  // Per-day y-offset (within ScrollView content) reported by DraggableWeekList
  // so we can scroll-anchor when the DayToggle is tapped.
  const dayOffsets = useRef<Map<string, number>>(new Map());
  // On web (iOS Safari), the parent ScrollView claims upward touches before
  // gesture-handler can. Disabling scroll during a drag lets the Pan win
  // in both directions.
  const [scrollEnabled, setScrollEnabled] = useState(true);

  const todayIsoStr = useMemo(() => toIso(new Date()), []);
  const todayCode = isoToDayCode(todayIsoStr);
  const [selectedDay, setSelectedDay] = useState<DayCode>(todayCode);

  // Reset selectedDay when cursor changes weeks: MON for any non-current week,
  // today's code when viewing today's week.
  useEffect(() => {
    const weekStart = toIso(startOfWeek(fromIso(cursorIso)));
    const todayWeekStart = toIso(startOfWeek(fromIso(todayIsoStr)));
    setSelectedDay(weekStart === todayWeekStart ? todayCode : 'MON');
  }, [cursorIso, todayCode, todayIsoStr]);

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

  const openDetail = (w: PlannedWorkoutOut) => {
    navigation.navigate('WorkoutDetail', { workoutId: w.id });
  };
  const requestMove = (w: PlannedWorkoutOut, newDate: string) => {
    void drag.requestMove(w, newDate).catch(() => {
      // surface error UX later; mutation already rolls back optimistic state
    });
  };

  const onPickDay = (code: DayCode) => {
    setSelectedDay(code);
    // Scroll-anchor the list to the picked day's tile. Offsets are populated
    // by DraggableWeekList's onDayLayout callback as each day View is measured.
    if (week.data === undefined) return;
    const idx = DAY_CODES.indexOf(code);
    if (idx < 0) return;
    const dayIso = toIso(addDays(fromIso(week.data.week_start), idx));
    const y = dayOffsets.current.get(dayIso);
    if (y !== undefined) {
      // Small offset (-8) so the day header isn't kissing the top of the viewport.
      scrollRef.current?.scrollTo({ y: Math.max(0, y - 8), animated: true });
    }
  };

  const recordDayOffset = useCallback((dayIso: string, y: number) => {
    dayOffsets.current.set(dayIso, y);
  }, []);

  const subhead = useMemo(() => {
    if (week.data === undefined) return 'LOADING…';
    const range = formatRange(week.data.week_start);
    const cycle = plan.data?.cycle_progress;
    if (cycle === null || cycle === undefined) return range;
    return `${range} — WK ${cycle.week} / ${cycle.total_weeks}`;
  }, [week.data, plan.data]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <BrandBanner subhead={subhead} />
      <View style={{ paddingHorizontal: 20, paddingTop: 4, paddingBottom: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Pressable onPress={goPrev} hitSlop={10} style={{ paddingHorizontal: 4, paddingVertical: 4 }}>
            <Text style={{ fontFamily: fonts.pixel, fontSize: 14, color: colors.ink }}>‹</Text>
          </Pressable>
          <View style={{ flex: 1 }}>
            <DayToggle<DayCode>
              options={DAY_CODES}
              value={selectedDay}
              highlight={todayCode}
              onChange={onPickDay}
            />
          </View>
          <Pressable onPress={goNext} hitSlop={10} style={{ paddingHorizontal: 4, paddingVertical: 4 }}>
            <Text style={{ fontFamily: fonts.pixel, fontSize: 14, color: colors.ink }}>›</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView
        ref={scrollRef}
        scrollEnabled={scrollEnabled}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 40 }}
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
            fontFamily: fonts.mono, fontSize: 11, color: colors.accentDanger, letterSpacing: 0.5,
          }}>
            Could not load week
          </Text>
        )}
        {week.data !== undefined && (
          <DraggableWeekList
            week={week.data}
            onWorkoutPress={openDetail}
            onMoveRequest={requestMove}
            disabled={drag.pending !== null}
            onDayLayout={recordDayOffset}
            onDragActive={(active) => { setScrollEnabled(!active); }}
          />
        )}
      </ScrollView>

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
