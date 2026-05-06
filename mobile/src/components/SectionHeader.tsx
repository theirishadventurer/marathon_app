import { Text, View } from 'react-native';

import { colors } from '@/theme/tokens';

interface Props {
  /** mixed-case label, e.g., "Day Session" — NOT all-caps */
  label: string;
  /** optional value rendered to the right (e.g., a count or status) */
  meta?: string;
}

/**
 * Section header in the staycation-informed style: cyan mixed-case mono
 * with a `▸` caret. Replaces ad-hoc all-caps PressStart2P 8pt headers
 * across screens for legibility.
 */
export function SectionHeader({ label, meta }: Props) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 16, marginBottom: 8 }}>
      <Text style={{
        fontFamily: 'VT323',
        fontSize: 18,
        color: colors.accentCyan,
        letterSpacing: 0.5,
      }}>
        ▸ {label}
      </Text>
      {meta !== undefined && (
        <>
          <View style={{ flex: 1 }} />
          <Text style={{
            fontFamily: 'VT323',
            fontSize: 14,
            color: colors.inkDim,
          }}>
            {meta}
          </Text>
        </>
      )}
    </View>
  );
}
