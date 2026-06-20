import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { CandidateOut, PlannedWorkoutOut } from '@/api/types';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts, radius } from '@/theme/tokens';

interface Props {
  workout: PlannedWorkoutOut | null;
  candidates: CandidateOut[];
  loading: boolean;
  submitting: boolean;
  onConfirm: (completedId: string) => void;
  onClose: () => void;
}

export const LinkRunSheet = forwardRef<BottomSheet, Props>(function LinkRunSheet(
  { workout, candidates, loading, submitting, onConfirm, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['55%', '85%'], []);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const canConfirm = selectedId !== null && !submitting;

  const submit = () => {
    if (selectedId === null) return;
    onConfirm(selectedId);
  };

  const badgeColor = (source: string) => {
    switch (source.toLowerCase()) {
      case 'garmin': return colors.accentCyan;
      case 'strava': return '#fc4c02';
      default: return colors.inkDim;
    }
  };

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
          Link a synced run
        </Text>
        {workout !== null && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginBottom: 18 }}>
            {workout.title}
          </Text>
        )}

        {loading && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginBottom: 16 }}>
            Looking for nearby activities…
          </Text>
        )}

        {!loading && candidates.length === 0 && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 13, color: colors.inkMute, marginBottom: 16 }}>
            No nearby synced runs found.
          </Text>
        )}

        {!loading && candidates.map((c) => {
          const isSelected = c.completed_id === selectedId;
          return (
            <Pressable
              key={c.completed_id}
              onPress={() => { setSelectedId(isSelected ? null : c.completed_id); }}
              style={{
                borderWidth: 2,
                borderColor: isSelected ? colors.accentRun : colors.line,
                borderRadius: radius.md,
                backgroundColor: isSelected ? colors.bgPanelAlt : colors.bgPanel,
                padding: 12,
                marginBottom: 10,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                <Text style={{ fontFamily: fonts.monoBold, fontSize: 13, color: colors.ink, flex: 1 }}>
                  {c.activity_date}
                </Text>
                <View style={{
                  backgroundColor: badgeColor(c.source),
                  borderRadius: radius.sm,
                  paddingHorizontal: 6,
                  paddingVertical: 2,
                }}>
                  <Text style={{ fontFamily: fonts.pixel, fontSize: 7, color: colors.bg }}>
                    {c.source.toUpperCase()}
                  </Text>
                </View>
              </View>
              <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginBottom: 2 }}>
                {c.activity_type}
              </Text>
              <View style={{ flexDirection: 'row', gap: 16 }}>
                {c.distance_mi !== null && (
                  <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.ink }}>
                    {c.distance_mi.toFixed(2)} mi
                  </Text>
                )}
                <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.ink }}>
                  {c.duration_min} min
                </Text>
                {c.avg_pace_str !== null && (
                  <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.inkDim }}>
                    {c.avg_pace_str} /mi
                  </Text>
                )}
              </View>
            </Pressable>
          );
        })}

        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
          <View style={{ flex: 1 }}>
            <RetroButton label="Cancel" onPress={onClose} disabled={submitting} />
          </View>
          <View style={{ flex: 1 }}>
            <RetroButton label="Link run" tone="primary" onPress={submit} disabled={!canConfirm} />
          </View>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
