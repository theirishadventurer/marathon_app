import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutSnapshot } from '@/api/types';
import { RetroButton } from '@/components/retro/RetroButton';
import { addDays, fromIso, toIso } from '@/lib/dates';
import { colors, fonts } from '@/theme/tokens';

const DAY_LABELS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

interface Props {
  snapshot: PlannedWorkoutSnapshot | null;
  weekStartIso: string | null;  // Monday of the week we're picking from
  submitting: boolean;
  onPick: (newDate: string) => void;
  onDrop: () => void;
  onClose: () => void;
}

export const DisplacedSheet = forwardRef<BottomSheet, Props>(function DisplacedSheet(
  { snapshot, weekStartIso, submitting, onPick, onDrop, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['55%'], []);
  const days = weekStartIso !== null
    ? Array.from({ length: 7 }, (_, i) => toIso(addDays(fromIso(weekStartIso), i)))
    : [];

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
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 16, color: colors.accentHi, marginBottom: 6 }}>
          Displaced
        </Text>
        <Text style={{ fontFamily: fonts.body, fontSize: 18, color: colors.ink, marginBottom: 16 }}>
          {snapshot?.title ?? '—'}
        </Text>
        <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 10, letterSpacing: 0.5 }}>
          Where should it go?
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 }}>
          {days.map((iso, i) => (
            <Pressable
              key={iso}
              onPress={() => { onPick(iso); }}
              disabled={submitting}
              style={{
                borderWidth: 2, borderColor: colors.line,
                backgroundColor: colors.bgPanelAlt,
                paddingHorizontal: 10, paddingVertical: 8, width: '22%',
              }}
            >
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.ink, textAlign: 'center', letterSpacing: 1 }}>
                {DAY_LABELS[i]}
              </Text>
            </Pressable>
          ))}
        </View>
        <RetroButton label="Drop it" tone="danger" onPress={onDrop} disabled={submitting} />
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
