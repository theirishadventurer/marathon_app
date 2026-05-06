import { Text, View } from 'react-native';

import { RetroBorder } from '@/components/retro/RetroBorder';
import { colors } from '@/theme/tokens';

interface Props {
  label: string;
  value: string;
  sub?: string;
  flex?: number;
}

export function StatTile({ label, value, sub, flex = 1 }: Props) {
  return (
    <View style={{ flex, marginHorizontal: 4 }}>
      <RetroBorder>
        <View style={{ padding: 12, minHeight: 76 }}>
          <Text style={{
            fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, letterSpacing: 1,
          }}>
            {label.toUpperCase()}
          </Text>
          <Text style={{
            fontFamily: 'VT323', fontSize: 22, color: colors.ink, marginTop: 4,
          }}>
            {value}
          </Text>
          {sub !== undefined && (
            <Text style={{
              fontFamily: 'VT323', fontSize: 14, color: colors.inkDim, marginTop: 2,
            }}>
              {sub}
            </Text>
          )}
        </View>
      </RetroBorder>
    </View>
  );
}
