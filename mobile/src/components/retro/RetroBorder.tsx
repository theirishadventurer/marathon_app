import type { PropsWithChildren } from 'react';
import { View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';
import { nesBorder, nesShadow } from '@/theme/retro';

interface Props {
  background?: string;
  noShadow?: boolean;
  style?: ViewStyle;
}

export function RetroBorder({
  children,
  background = colors.bgPanel,
  noShadow = false,
  style,
}: PropsWithChildren<Props>) {
  return (
    <View
      style={[
        nesBorder(),
        noShadow ? null : nesShadow(),
        { backgroundColor: background },
        style,
      ]}
    >
      {children}
    </View>
  );
}
