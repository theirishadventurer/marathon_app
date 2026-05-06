import { Text, View } from 'react-native';

import { colors, radius } from '@/theme/tokens';

type Variant = 'bracket' | 'badge';

interface Props {
  label: string;
  /**
   * "bracket": [ LABEL ] inline text-only — current default for status.
   * "badge": filled rounded chip — for family/platform/category tags.
   */
  variant?: Variant;
  /** for badge variant: background fill */
  background?: string;
  /** for both variants: text color */
  color?: string;
}

export function RetroPill({
  label,
  variant = 'bracket',
  background = colors.bgPanelAlt,
  color = colors.inkDim,
}: Props) {
  if (variant === 'bracket') {
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
  return (
    <View
      style={{
        backgroundColor: background,
        borderRadius: radius.sm,
        paddingHorizontal: 6,
        paddingVertical: 2,
        alignSelf: 'flex-start',
      }}
    >
      <Text
        style={{
          color,
          fontFamily: 'PressStart2P',
          fontSize: 8,
          letterSpacing: 1,
        }}
      >
        {label.toUpperCase()}
      </Text>
    </View>
  );
}
