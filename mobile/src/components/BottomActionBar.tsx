import type { PropsWithChildren } from 'react';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme/tokens';

/**
 * Fixed-position bottom action bar with a 1px top border and safe-area
 * inset padding. Children laid horizontally with even spacing.
 *
 * Used by WorkoutDetail (MARK DONE / SKIP) and any future screen that
 * wants a fixed pair-of-actions affordance at the bottom.
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
