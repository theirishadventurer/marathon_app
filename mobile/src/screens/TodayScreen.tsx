import BottomSheet from '@gorhom/bottom-sheet';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanToday } from '@/api/hooks/usePlan';
import type { PlannedWorkoutOut } from '@/api/types';
import { WorkoutCard } from '@/components/WorkoutCard';
import { WhySheet } from '@/components/WhySheet';
import { fromIso } from '@/lib/dates';
import type { RootStackParamList } from '@/navigation/types';

function formatHeaderDate(iso: string): string {
  return fromIso(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });
}

export function TodayScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const today = usePlanToday();
  const plan = usePlanCurrent();
  const sheetRef = useRef<BottomSheet>(null);
  const [whyWorkout, setWhyWorkout] = useState<PlannedWorkoutOut | null>(null);

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
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={today.isFetching || plan.isFetching}
            onRefresh={() => { void onRefresh(); }}
            tintColor="#a1a1aa"
          />
        }
      >
        <Text className="text-ink-dim text-xs uppercase tracking-wide">
          {today.data !== undefined ? formatHeaderDate(today.data.date) : 'Today'}
        </Text>
        <Text className="text-ink text-3xl font-bold mt-1 mb-1">What&apos;s on tap</Text>
        {plan.data?.cycle_progress !== null && plan.data?.cycle_progress !== undefined && (
          <Text className="text-ink-dim text-sm mb-4">
            Week {plan.data.cycle_progress.week} of {plan.data.cycle_progress.total_weeks} ·{' '}
            {plan.data.cycle_progress.days_to_race} days to {plan.data.active_cycle?.race_name ?? 'race'}
          </Text>
        )}

        <View className="bg-bg-card rounded-xl p-4 mb-6 border border-line">
          <Text className="text-ink-dim text-xs uppercase mb-2">Coach brief</Text>
          <Text className="text-ink-dim italic">Coach brief — wired in session 3</Text>
        </View>

        {today.isLoading && (
          <View className="items-center py-10">
            <ActivityIndicator color="#34d399" />
          </View>
        )}

        {today.isError && (
          <Text className="text-accent-danger">Could not load today&apos;s plan.</Text>
        )}

        {today.data !== undefined && today.data.workouts.length === 0 && !today.isLoading && (
          <View className="bg-bg-card rounded-xl p-6 items-center border border-line">
            <Text className="text-ink-dim">Rest day. No work scheduled.</Text>
          </View>
        )}

        {today.data?.workouts.map((w) => (
          <WorkoutCard
            key={w.id}
            workout={w}
            onPress={() => { openDetail(w); }}
            onWhy={() => { openWhy(w); }}
          />
        ))}

        <Text className="text-ink-dim text-xs uppercase mt-8 mb-3">Recent runs</Text>
        <View className="bg-bg-card rounded-xl p-4 border border-line">
          <Text className="text-ink-dim text-sm">
            Recent runs strip lands once `/workouts/completed/recent` ships.
          </Text>
        </View>
      </ScrollView>

      <WhySheet ref={sheetRef} workout={whyWorkout} onClose={closeWhy} />
    </SafeAreaView>
  );
}
