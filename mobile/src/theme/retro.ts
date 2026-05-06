import { type ViewStyle } from 'react-native';
import { Easing } from 'react-native-reanimated';

import { colors } from './tokens';

export const stepEasing = Easing.steps(4);

export function nesShadow(offset = 2): ViewStyle {
  return {
    shadowColor: '#000',
    shadowOffset: { width: offset, height: offset },
    shadowOpacity: 1,
    shadowRadius: 0,
    elevation: offset,
  };
}

export function nesBorder(width = 2): ViewStyle {
  return {
    borderWidth: width,
    borderColor: colors.line,
    borderRadius: 0,
  };
}
