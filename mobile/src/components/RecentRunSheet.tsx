import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Text, View } from 'react-native';

import type { CompletedWorkoutOut } from '@/api/types';
import { fromIso } from '@/lib/dates';
import { colors, fonts } from '@/theme/tokens';

interface Props {
  run: CompletedWorkoutOut | null;
  onClose: () => void;
}

const _METERS_PER_MILE = 1609.344;

function metersToMiles(m: string | null): string {
  if (m === null) return '—';
  const v = parseFloat(m);
  if (Number.isNaN(v)) return '—';
  return `${(v / _METERS_PER_MILE).toFixed(2)}mi`;
}

function durationToHmm(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function paceFromActivity(distance_m: string | null, duration_s: number): string {
  if (distance_m === null) return '—';
  const v = parseFloat(distance_m);
  if (Number.isNaN(v) || v <= 0 || duration_s <= 0) return '—';
  const mi = v / _METERS_PER_MILE;
  const sPerMi = Math.round(duration_s / mi);
  const m = Math.floor(sPerMi / 60);
  const s = sPerMi % 60;
  return `${m}:${String(s).padStart(2, '0')}/mi`;
}

export const RecentRunSheet = forwardRef<BottomSheet, Props>(function RecentRunSheet(
  { run, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['50%', '85%'], []);
  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {run === null ? (
          <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim }}>
            No run selected.
          </Text>
        ) : (
          <View>
            <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5, marginBottom: 4 }}>
              {fromIso(run.activity_date).toLocaleDateString('en-US', {
                weekday: 'long', month: 'short', day: 'numeric',
              }).toUpperCase()}
            </Text>
            <Text style={{ fontFamily: fonts.monoBold, fontSize: 22, color: colors.ink, marginBottom: 14 }}>
              {run.activity_type.replace(/_/g, ' ')}
            </Text>

            <Stat label="DISTANCE" value={metersToMiles(run.distance_m)} />
            <Stat label="DURATION" value={durationToHmm(run.duration_s)} />
            <Stat label="AVG PACE" value={paceFromActivity(run.distance_m, run.duration_s)} />
            <Stat label="AVG HR" value={run.avg_hr !== null ? `${run.avg_hr} bpm` : '—'} />
            <Stat label="MAX HR" value={run.max_hr !== null ? `${run.max_hr} bpm` : '—'} />
            <Stat label="ELEVATION" value={run.elevation_gain_m !== null ? `${parseFloat(run.elevation_gain_m).toFixed(0)} m` : '—'} />
            <Stat label="CALORIES" value={run.calories !== null ? String(run.calories) : '—'} />
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.line }}>
      <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5 }}>
        {label}
      </Text>
      <Text style={{ fontFamily: fonts.monoBold, fontSize: 16, color: colors.ink }}>
        {value}
      </Text>
    </View>
  );
}
