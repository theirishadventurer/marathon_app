import { useState } from 'react';
import { Pressable, Text, View, type ViewStyle } from 'react-native';

import { colors } from '@/theme/tokens';
import { nesBorder, nesShadow } from '@/theme/retro';

type Tone = 'default' | 'primary' | 'danger' | 'ghost';

interface Props {
  label: string;
  onPress?: () => void;
  disabled?: boolean;
  tone?: Tone;
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

export function RetroButton({
  label, onPress, disabled = false, tone = 'default', style,
}: Props) {
  const [pressed, setPressed] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => { setPressed(true); }}
      onPressOut={() => { setPressed(false); }}
      disabled={disabled}
      style={[
        nesBorder(),
        pressed ? null : nesShadow(),
        {
          backgroundColor: TONE_BG[tone],
          paddingHorizontal: 14,
          paddingVertical: 10,
          opacity: disabled ? 0.4 : 1,
          transform: pressed ? [{ translateX: 2 }, { translateY: 2 }] : [],
        },
        style,
      ]}
    >
      <View>
        <Text
          style={{
            color: TONE_INK[tone],
            fontFamily: 'PressStart2P',
            fontSize: 10,
            letterSpacing: 1,
            textAlign: 'center',
          }}
        >
          {label.toUpperCase()}
        </Text>
      </View>
    </Pressable>
  );
}
