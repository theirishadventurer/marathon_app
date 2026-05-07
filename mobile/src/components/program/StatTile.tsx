import { Text, View } from 'react-native';

import { RetroBorder } from '@/components/retro/RetroBorder';
import { colors, fonts } from '@/theme/tokens';

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
        <View style={{ padding: 12, minHeight: 80 }}>
          <Text style={{
            fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5,
          }}>
            {label}
          </Text>
          <Text style={{
            fontFamily: fonts.monoBold, fontSize: 22, color: colors.ink, marginTop: 4,
          }}>
            {value}
          </Text>
          {sub !== undefined && (
            <Text style={{
              fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginTop: 2,
            }}>
              {sub}
            </Text>
          )}
        </View>
      </RetroBorder>
    </View>
  );
}
