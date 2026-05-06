import { Text, View } from 'react-native';

import { colors } from '@/theme/tokens';

interface Props {
  label: string;
  color?: string;
}

export function RetroPill({ label, color = colors.inkDim }: Props) {
  return (
    <View>
      <Text
        style={{
          color,
          fontFamily: 'PressStart2P',
          fontSize: 8,
          letterSpacing: 1,
        }}
      >
        [ {label.toUpperCase()} ]
      </Text>
    </View>
  );
}
