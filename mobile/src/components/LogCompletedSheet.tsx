import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useEffect, useMemo, useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';

import type { LogCompletedRequest, PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts, radius } from '@/theme/tokens';

interface Props {
  workout: PlannedWorkoutOut | null;
  submitting: boolean;
  onConfirm: (body: LogCompletedRequest) => void;
  onClose: () => void;
  onSync?: () => void;
  syncPending?: boolean;
}

export const LogCompletedSheet = forwardRef<BottomSheet, Props>(function LogCompletedSheet(
  { workout, submitting, onConfirm, onClose, onSync, syncPending = false }, ref,
) {
  const snapPoints = useMemo(() => ['65%', '95%'], []);
  const isRunning = workout?.family === 'running';
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [showMore, setShowMore] = useState(false);
  const [pace, setPace] = useState('');
  const [hr, setHr] = useState('');
  const [notes, setNotes] = useState('');

  // Reset form when target workout changes
  useEffect(() => {
    setDistance(workout?.distance_mi !== null && workout?.distance_mi !== undefined ? String(workout.distance_mi) : '');
    setDuration(workout?.duration_min !== null && workout?.duration_min !== undefined ? String(workout.duration_min) : '');
    setShowMore(false);
    setPace('');
    setHr('');
    setNotes('');
  }, [workout?.id]);

  const distanceRequired = isRunning;
  const distanceValid = !distanceRequired || (parseFloat(distance) > 0);
  const durationValid = parseInt(duration, 10) > 0;
  const canConfirm = distanceValid && durationValid && !submitting;

  const submit = () => {
    const body: LogCompletedRequest = {
      duration_min: parseInt(duration, 10),
    };
    const d = parseFloat(distance);
    if (!Number.isNaN(d) && d > 0) body.distance_mi = d;
    if (pace.length > 0) body.avg_pace_str = pace;
    if (hr.length > 0) {
      const n = parseInt(hr, 10);
      if (!Number.isNaN(n)) body.avg_hr = n;
    }
    if (notes.length > 0) body.notes = notes;
    onConfirm(body);
  };

  const inputStyle = {
    fontFamily: fonts.mono,
    fontSize: 16,
    color: colors.ink,
    padding: 8,
    borderWidth: 2,
    borderColor: colors.line,
    borderRadius: radius.sm,
    marginBottom: 10,
  } as const;

  const labelStyle = {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.inkDim,
    marginBottom: 4,
    letterSpacing: 0.5,
  } as const;

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
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 22, color: colors.accentHi, marginBottom: 14 }}>
          Mark done
        </Text>
        {workout !== null && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginBottom: 18 }}>
            {workout.title}
          </Text>
        )}

        {distanceRequired && (
          <>
            <Text style={labelStyle}>DISTANCE (MI)</Text>
            <TextInput
              value={distance}
              onChangeText={setDistance}
              keyboardType="decimal-pad"
              placeholder="5.0"
              placeholderTextColor={colors.inkMute}
              style={inputStyle}
            />
          </>
        )}

        <Text style={labelStyle}>DURATION (MIN)</Text>
        <TextInput
          value={duration}
          onChangeText={setDuration}
          keyboardType="number-pad"
          placeholder="50"
          placeholderTextColor={colors.inkMute}
          style={inputStyle}
        />

        <Pressable onPress={() => { setShowMore((s) => !s); }} hitSlop={6}>
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentRun, marginTop: 4, marginBottom: 10 }}>
            {showMore ? '▾ HIDE MORE STATS' : '▸ MORE STATS'}
          </Text>
        </Pressable>

        {showMore && (
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 14 }}>
            <View style={{ padding: 12 }}>
              <Text style={labelStyle}>AVG PACE (MM:SS)</Text>
              <TextInput
                value={pace}
                onChangeText={setPace}
                placeholder="10:45"
                placeholderTextColor={colors.inkMute}
                style={inputStyle}
              />
              <Text style={labelStyle}>AVG HR (BPM)</Text>
              <TextInput
                value={hr}
                onChangeText={setHr}
                keyboardType="number-pad"
                placeholder="142"
                placeholderTextColor={colors.inkMute}
                style={inputStyle}
              />
              <Text style={labelStyle}>NOTES</Text>
              <TextInput
                value={notes}
                onChangeText={setNotes}
                multiline
                numberOfLines={3}
                placeholder="How did it feel?"
                placeholderTextColor={colors.inkMute}
                style={[inputStyle, { minHeight: 60, textAlignVertical: 'top' }]}
              />
            </View>
          </RetroBorder>
        )}

        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
          <View style={{ flex: 1 }}>
            <RetroButton label="Cancel" onPress={onClose} disabled={submitting} />
          </View>
          <View style={{ flex: 1 }}>
            <RetroButton label="Confirm" tone="primary" onPress={submit} disabled={!canConfirm} />
          </View>
        </View>

        {onSync !== undefined && (
          <Pressable
            onPress={onSync}
            disabled={syncPending}
            hitSlop={8}
            style={{ marginTop: 16, alignSelf: 'center' }}
          >
            <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentCyan }}>
              {syncPending ? 'Syncing…' : 'or sync from Garmin →'}
            </Text>
          </Pressable>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
