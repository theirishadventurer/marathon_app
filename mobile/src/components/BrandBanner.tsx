import { Text, View } from 'react-native';

import { colors, fonts } from '@/theme/tokens';

interface Props {
  /** mono-caps subhead text shown after the `▸` caret, e.g. "MARATHON_TRILOGY — WK 4 / 28 · MCM 173d" */
  subhead: string;
  /** top-right meta chip; default `v1.0 ◦` */
  meta?: string;
}

/**
 * Top-of-screen brand banner used on every content screen. Renders the
 * `MARATHON` wordmark in phosphor green, a small mono meta chip top-right,
 * a `▸` caret subhead in dim mono caps, and a 1px slate horizontal rule.
 *
 * Pattern source: docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md §5.1.
 */
export function BrandBanner({ subhead, meta = 'v1.0 ◦' }: Props) {
  return (
    <View style={{ paddingHorizontal: 20, paddingTop: 12, paddingBottom: 16 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{
          fontFamily: fonts.pixel,
          fontSize: 24,
          color: colors.accentRun,
          letterSpacing: 2,
        }}>
          MARATHON
        </Text>
        <Text style={{
          fontFamily: fonts.mono,
          fontSize: 11,
          color: colors.inkDim,
        }}>
          {meta}
        </Text>
      </View>
      <Text style={{
        fontFamily: fonts.mono,
        fontSize: 12,
        color: colors.inkDim,
        letterSpacing: 0.5,
        marginTop: 4,
      }}>
        ▸ {subhead}
      </Text>
      <View style={{
        height: 1,
        backgroundColor: colors.line,
        marginTop: 12,
      }} />
    </View>
  );
}
