import { useState } from 'react';
import { Pressable, Text, View, type ViewStyle } from 'react-native';

import { colors, fonts, radius } from '@/theme/tokens';
import { softBorder } from '@/theme/retro';

type Tone = 'default' | 'primary' | 'danger' | 'ghost';
type Display = 'pixel' | 'mono';

interface Props {
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  tone?: Tone;
  /**
   * Typography style. Defaults to 'mono' for default/danger/ghost tones and
   * 'pixel' for primary tone (preserves the "press start" feel on key CTAs).
   * Pass explicitly to override.
   */
  display?: Display;
  style?: ViewStyle;
}

const TONE_BG: Record<Tone, string> = {
  default: colors.bgPanelAlt,
  primary: colors.accentRun,
  danger: colors.accentDanger,
  ghost: 'transparent',
};

const TONE_INK: Record<Tone, string> = {
  default: colors.ink,
  primary: colors.bg,
  danger: colors.ink,
  ghost: colors.ink,
};

const TONE_BORDER: Record<Tone, boolean> = {
  default: true,
  primary: false,   // primary CTAs are filled, no border
  danger: true,
  ghost: true,
};

export function RetroButton({
  label, onPress, disabled = false, tone = 'default', display, style,
}: Props) {
  const [pressed, setPressed] = useState(false);
  const showBorder = TONE_BORDER[tone];
  const resolvedDisplay: Display = display ?? (tone === 'primary' ? 'pixel' : 'mono');
  const isPixel = resolvedDisplay === 'pixel';
  const fontFamily = isPixel ? fonts.pixel : fonts.mono;
  const fontSize = isPixel ? 10 : 12;
  const letterSpacing = isPixel ? 1 : 0;
  const labelText = isPixel ? label.toUpperCase() : label;
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => { setPressed(true); }}
      onPressOut={() => { setPressed(false); }}
      disabled={disabled}
      style={[
        showBorder ? softBorder(1, radius.md) : { borderRadius: radius.md },
        {
          backgroundColor: TONE_BG[tone],
          paddingHorizontal: 14,
          paddingVertical: 10,
          opacity: disabled ? 0.4 : 1,
          transform: pressed ? [{ translateX: 1 }, { translateY: 1 }] : [],
        },
        style,
      ]}
    >
      <View>
        <Text
          style={{
            color: TONE_INK[tone],
            fontFamily,
            fontSize,
            letterSpacing,
            textAlign: 'center',
          }}
        >
          {labelText}
        </Text>
      </View>
    </Pressable>
  );
}
