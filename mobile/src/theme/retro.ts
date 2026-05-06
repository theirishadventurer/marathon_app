import { type ViewStyle } from 'react-native';
import { Easing } from 'react-native-reanimated';

import { colors, radius } from './tokens';

export const stepEasing = Easing.steps(4);

/**
 * Hard offset NES shadow. Kept for parity with code that explicitly opts in.
 * Most surfaces should use `noShadow()` (i.e., omit shadow) per the staycation
 * polish — elevation comes from the slightly-lifted bgPanel tone now.
 */
export function nesShadow(offset = 2): ViewStyle {
  return {
    shadowColor: '#000',
    shadowOffset: { width: offset, height: offset },
    shadowOpacity: 1,
    shadowRadius: 0,
    elevation: offset,
  };
}

/**
 * Legacy hard 2px black border + 0 radius. Avoid in new code.
 * Kept so existing call sites don't break before they're migrated.
 */
export function nesBorder(width = 2): ViewStyle {
  return {
    borderWidth: width,
    borderColor: colors.lineHard,
    borderRadius: 0,
  };
}

/**
 * Default soft border used everywhere from polish onward.
 * 1px slate line + 4px radius. Pair with `bgPanel` for subtle elevation.
 */
export function softBorder(width = 1, r: number = radius.md): ViewStyle {
  return {
    borderWidth: width,
    borderColor: colors.line,
    borderRadius: r,
  };
}
