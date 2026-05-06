import type { PropsWithChildren } from 'react';
import { View, type ViewStyle } from 'react-native';

import { RetroBorder } from './RetroBorder';

interface Props {
  style?: ViewStyle;
  padding?: number;
}

export function RetroCard({
  children, style, padding = 14,
}: PropsWithChildren<Props>) {
  return (
    <RetroBorder style={style}>
      <View style={{ padding }}>{children}</View>
    </RetroBorder>
  );
}
