import { Pressable, Text, View } from 'react-native';

import { colors, fonts, radius, spacing } from '@/theme/tokens';

interface Props<T extends string> {
  /** Segment labels in display order, e.g. ['TODAY','TOMORROW'] or ['MON','TUE',...,'SUN']. */
  options: readonly T[];
  /** Currently selected option. Must be present in `options`. */
  value: T;
  /** Callback fired when the user taps a segment. */
  onChange: (v: T) => void;
  /** Optional "today" highlight (different from selected). E.g. when value='WED' but today is 'FRI'. */
  highlight?: T;
}

/**
 * Generic segmented pill. Active segment renders filled phosphor green
 * with pixel-font white text. Inactive segments transparent with mono
 * cream text. Highlight (the "real today" when not selected) shows in
 * phosphor green text on transparent.
 *
 * 1px slate dividers between segments form a single rounded outer pill.
 *
 * Pattern source: docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md §5.4.
 */
export function DayToggle<T extends string>({ options, value, onChange, highlight }: Props<T>) {
  return (
    <View style={{
      flexDirection: 'row',
      borderWidth: 1,
      borderColor: colors.line,
      borderRadius: radius.lg,
      overflow: 'hidden',
    }}>
      {options.map((opt, idx) => {
        const isActive = opt === value;
        const isHighlight = highlight === opt && !isActive;
        const showDivider = idx > 0;
        return (
          <View key={opt} style={{ flex: 1, flexDirection: 'row' }}>
            {showDivider && (
              <View style={{ width: 1, backgroundColor: colors.line }} />
            )}
            <Pressable
              onPress={() => { onChange(opt); }}
              hitSlop={4}
              style={{
                flex: 1,
                backgroundColor: isActive ? colors.accentRun : 'transparent',
                paddingVertical: spacing.sm,
                paddingHorizontal: 6,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Text style={{
                fontFamily: isActive ? fonts.pixel : fonts.mono,
                fontSize: isActive ? 10 : 12,
                color: isActive ? colors.bg : (isHighlight ? colors.accentRun : colors.ink),
                letterSpacing: isActive ? 1 : 0.5,
              }}>
                {opt}
              </Text>
            </Pressable>
          </View>
        );
      })}
    </View>
  );
}
