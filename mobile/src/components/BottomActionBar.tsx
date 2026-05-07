import type { PropsWithChildren } from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme/tokens';

/**
 * Bottom action row: 1px top border, bgPanel background, safe-area
 * inset padding, children laid flex-row with even gap. Designed to be
 * placed as the last child of a SafeAreaView (sibling to a flex-1
 * ScrollView) so normal flex layout pushes it to the bottom — no
 * absolute positioning. Children typically a pair of RetroButtons
 * each wrapped in a `<View style={{ flex: 1 }}>` to share row width.
 *
 * Used by WorkoutDetail (MARK DONE / SKIP). Optimized for 2-3 children;
 * more than that will compress the even-gap layout.
 *
 * Pattern source: docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md §5.7.
 */
export function BottomActionBar({ children }: PropsWithChildren<unknown>) {
  const insets = useSafeAreaInsets();
  return (
    <View style={{
      borderTopWidth: 1,
      borderTopColor: colors.line,
      backgroundColor: colors.bgPanel,
      paddingHorizontal: spacing.lg,
      paddingTop: spacing.md,
      paddingBottom: spacing.md + insets.bottom,
      flexDirection: 'row',
      gap: spacing.md,
    }}>
      {children}
    </View>
  );
}
