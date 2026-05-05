import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Text, View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import type { PlannedWorkoutOut } from '@/api/types';
import { colors } from '@/theme/tokens';

interface Props {
  workout: PlannedWorkoutOut | null;
  onClose: () => void;
}

const markdownStyle = {
  body: { color: colors.ink, fontSize: 15, lineHeight: 22 },
  heading1: { color: colors.ink, fontSize: 20, fontWeight: '700' as const, marginTop: 12, marginBottom: 8 },
  heading2: { color: colors.ink, fontSize: 17, fontWeight: '700' as const, marginTop: 12, marginBottom: 6 },
  heading3: { color: colors.ink, fontSize: 15, fontWeight: '700' as const, marginTop: 10, marginBottom: 4 },
  paragraph: { color: colors.ink, marginBottom: 8 },
  code_inline: { color: colors.accentRun, backgroundColor: colors.bgElev, paddingHorizontal: 4, borderRadius: 4 },
  bullet_list: { marginBottom: 8 },
  list_item: { color: colors.ink },
  strong: { color: colors.ink, fontWeight: '700' as const },
  em: { color: colors.ink, fontStyle: 'italic' as const },
  hr: { backgroundColor: colors.line, height: 1, marginVertical: 12 },
};

export const WhySheet = forwardRef<BottomSheet, Props>(function WhySheet(
  { workout, onClose },
  ref,
) {
  const snapPoints = useMemo(() => ['60%', '90%'], []);
  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgElev }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {workout === null ? (
          <Text style={{ color: colors.inkDim }}>No workout selected.</Text>
        ) : (
          <View>
            <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase' }}>
              Week {workout.week_number} · {workout.type}
            </Text>
            <Text style={{ color: colors.ink, fontSize: 22, fontWeight: '700', marginTop: 4, marginBottom: 14 }}>
              {workout.title}
            </Text>
            {workout.description_md.trim().length > 0 && (
              <View>
                <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 4 }}>
                  Prescription
                </Text>
                <Markdown style={markdownStyle}>{workout.description_md}</Markdown>
              </View>
            )}
            {workout.intent_md.trim().length > 0 && (
              <View style={{ marginTop: 16 }}>
                <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase', marginBottom: 4 }}>
                  Intent
                </Text>
                <Markdown style={markdownStyle}>{workout.intent_md}</Markdown>
              </View>
            )}
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
