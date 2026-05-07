import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo } from 'react';
import { Text, View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import type { PlannedWorkoutOut } from '@/api/types';
import { colors, fonts } from '@/theme/tokens';

interface Props {
  workout: PlannedWorkoutOut | null;
  onClose: () => void;
}

const markdownStyle = {
  body: { color: colors.ink, fontFamily: fonts.body, fontSize: 18, lineHeight: 22 },
  heading1: { color: colors.ink, fontFamily: fonts.monoBold, fontSize: 16, marginTop: 12, marginBottom: 8 },
  heading2: { color: colors.ink, fontFamily: fonts.monoBold, fontSize: 14, marginTop: 12, marginBottom: 6 },
  heading3: { color: colors.ink, fontFamily: fonts.monoBold, fontSize: 12, marginTop: 10, marginBottom: 4 },
  paragraph: { color: colors.ink, marginBottom: 8 },
  code_inline: { color: colors.accentHi, backgroundColor: colors.bgPanelAlt, paddingHorizontal: 4 },
  bullet_list: { marginBottom: 8 },
  list_item: { color: colors.ink },
  strong: { color: colors.ink, fontFamily: fonts.monoBold, fontSize: 18 },
  em: { color: colors.ink, fontStyle: 'italic' as const },
  hr: { backgroundColor: colors.line, height: 2, marginVertical: 12 },
};

export const WhySheet = forwardRef<BottomSheet, Props>(function WhySheet(
  { workout, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['60%', '90%'], []);
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
        {workout === null ? (
          <Text style={{ fontFamily: fonts.body, fontSize: 18, color: colors.inkDim }}>
            No workout selected.
          </Text>
        ) : (
          <View>
            <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5 }}>
              WK {workout.week_number} · {workout.type.toUpperCase()}
            </Text>
            <Text style={{ fontFamily: fonts.monoBold, fontSize: 20, color: colors.ink, marginTop: 6, marginBottom: 18 }}>
              {workout.title}
            </Text>
            {workout.description_md.trim().length > 0 && (
              <View>
                <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5, marginBottom: 4 }}>
                  PRESCRIPTION
                </Text>
                <Markdown style={markdownStyle}>{workout.description_md}</Markdown>
              </View>
            )}
            {workout.intent_md.trim().length > 0 && (
              <View style={{ marginTop: 16 }}>
                <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5, marginBottom: 4 }}>
                  INTENT
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
