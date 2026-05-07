import { useNavigation } from '@react-navigation/native';
import type { CompositeNavigationProp } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useMemo } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePlanCurrent, usePlanFull, useProgressStats } from '@/api/hooks/usePlan';
import { CycleLane } from '@/components/program/CycleLane';
import { StatsPanel } from '@/components/program/StatsPanel';
import { WeeklyMileageTracker } from '@/components/program/WeeklyMileageTracker';
import type { RootStackParamList, TabParamList } from '@/navigation/types';
import { colors, fonts } from '@/theme/tokens';

type Nav = CompositeNavigationProp<
  BottomTabNavigationProp<TabParamList, 'Program'>,
  NativeStackNavigationProp<RootStackParamList>
>;

export function ProgramScreen() {
  const navigation = useNavigation<Nav>();
  const planFull = usePlanFull();
  const stats = useProgressStats('cycle');
  const planCurrent = usePlanCurrent();

  const activeCycleId = useMemo(() => {
    if (planFull.data === undefined) return null;
    const today = new Date().toISOString().slice(0, 10);
    const active = planFull.data.cycles.find(
      (c) => c.start_date <= today && c.end_date >= today,
    );
    return active?.id ?? planFull.data.cycles[0]?.id ?? null;
  }, [planFull.data]);

  const onRefresh = async () => {
    await Promise.all([planFull.refetch(), stats.refetch(), planCurrent.refetch()]);
  };

  const onWeekPress = (weekStartIso: string) => {
    navigation.navigate('Tabs', {
      screen: 'Week',
      params: { initialDate: weekStartIso },
    });
  };

  const onRacePress = (workoutId: string) => {
    navigation.navigate('WorkoutDetail', { workoutId });
  };

  const refreshing = planFull.isFetching || stats.isFetching;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { void onRefresh(); }}
            tintColor={colors.inkDim}
          />
        }
      >
        <View style={{ marginBottom: 24 }}>
          <Text style={{
            fontFamily: fonts.pixel, fontSize: 16, color: colors.ink, letterSpacing: 1,
          }}>
            PROGRAM
          </Text>
          <Text style={{
            fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginTop: 4,
          }}>
            {planFull.data?.plan_name ?? 'Loading…'}
          </Text>
        </View>

        {planFull.isLoading || stats.isLoading || planCurrent.isLoading ? (
          <View style={{ alignItems: 'center', paddingVertical: 40 }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        ) : null}

        {planFull.isError || stats.isError ? (
          <Text style={{
            fontFamily: fonts.mono, fontSize: 11, color: colors.accentDanger, letterSpacing: 0.5,
          }}>
            Could not load program
          </Text>
        ) : null}

        {stats.data !== undefined && planCurrent.data !== undefined && (
          <View style={{ marginBottom: 16 }}>
            <StatsPanel stats={stats.data} plan={planCurrent.data} />
          </View>
        )}

        {planFull.data !== undefined && (
          <View style={{ flexDirection: 'row', height: 520, marginBottom: 16 }}>
            {planFull.data.cycles.map((c) => (
              <CycleLane
                key={c.id}
                cycle={c}
                onWeekPress={onWeekPress}
                onRacePress={onRacePress}
              />
            ))}
          </View>
        )}

        {planFull.data !== undefined && (
          <WeeklyMileageTracker
            cycles={planFull.data.cycles}
            defaultCycleId={activeCycleId}
            onWeekPress={onWeekPress}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
