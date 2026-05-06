import { Pressable, Text } from 'react-native';

import { colors, radius } from '@/theme/tokens';
import { softBorder } from '@/theme/retro';

interface Props {
  raceName: string;
  raceDate: string;  // ISO YYYY-MM-DD
  onPress?: () => void;
}

function formatRaceDate(iso: string): string {
  const parts = iso.split('-');
  const m = parts[1] ?? '';
  const d = parts[2] ?? '';
  return `${parseInt(m, 10)}/${parseInt(d, 10)}`;
}

export function RaceMilestoneTile({ raceName, raceDate, onPress }: Props) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        softBorder(2, radius.md),
        {
          backgroundColor: colors.accentHi,
          borderColor: colors.lineHard,
          paddingHorizontal: 10,
          paddingVertical: 12,
          marginTop: 8,
          alignItems: 'center',
        },
      ]}
    >
      <Text style={{
        fontFamily: 'PressStart2P', fontSize: 14, color: colors.bg, letterSpacing: 1,
      }}>
        ⚑ {raceName.toUpperCase()}
      </Text>
      <Text style={{
        fontFamily: 'VT323', fontSize: 14, color: colors.bg, marginTop: 4,
      }}>
        {formatRaceDate(raceDate)}
      </Text>
    </Pressable>
  );
}
