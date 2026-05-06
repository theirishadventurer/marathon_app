import type { PropsWithChildren } from 'react';
import { View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';
import { nesShadow, softBorder } from '@/theme/retro';

interface Props {
  background?: string;
  /** opt back into the legacy hard offset shadow for one-off surfaces */
  legacyShadow?: boolean;
  /** custom corner radius; default 6 */
  radius?: number;
  style?: ViewStyle;
}

export function RetroBorder({
  children,
  background = colors.bgPanel,
  legacyShadow = false,
  radius = 6,
  style,
}: PropsWithChildren<Props>) {
  return (
    <View
      style={[
        softBorder(1, radius),
        legacyShadow ? nesShadow() : null,
        { backgroundColor: background },
        style,
      ]}
    >
      {children}
    </View>
  );
}
