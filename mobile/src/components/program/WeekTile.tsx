import { Pressable, Text } from 'react-native';

import type { WeekRollup } from '@/api/types';
import { colors, radius } from '@/theme/tokens';
import { softBorder } from '@/theme/retro';

interface Props {
  week: WeekRollup;
  onPress?: () => void;
}

const STATUS_BG: Record<WeekRollup['status'], string> = {
  done: colors.accentRun,
  partial: colors.accentDanger,
  current: colors.accentHi,
  upcoming: colors.bgPanel,
  skipped: colors.accentDanger,
};

const STATUS_INK: Record<WeekRollup['status'], string> = {
  done: colors.bg,
  partial: colors.ink,
  current: colors.bg,
  upcoming: colors.inkDim,
  skipped: colors.ink,
};

function formatMileageGlyph(week: WeekRollup): string {
  const planned = parseFloat(week.planned_mi);
  const actual = parseFloat(week.actual_mi);
  if (week.has_race) return `[FLAG]`;
  if (week.is_peak) return `★ ${Math.round(planned)}mi`;
  if (week.is_cutback) return `↓ ${Math.round(planned)}mi`;
  if (week.status === 'done' && actual >= planned) return `✓ ${Math.round(actual)}mi`;
  if (week.status === 'done') return `✓ ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  if (week.status === 'current') {
    return `▶ ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  }
  if (week.status === 'partial' || week.status === 'skipped') {
    return `! ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  }
  return `— ${Math.round(planned)}mi`;
}

export function WeekTile({ week, onPress }: Props) {
  const bg = STATUS_BG[week.status];
  const ink = STATUS_INK[week.status];
  const isUpcoming = week.status === 'upcoming';
  const showCutbackBorder = week.is_cutback && !isUpcoming;

  return (
    <Pressable
      onPress={onPress}
      style={[
        softBorder(showCutbackBorder ? 2 : 1, radius.md),
        {
          backgroundColor: bg,
          borderColor: showCutbackBorder ? colors.accentRest : colors.line,
          paddingHorizontal: 10,
          paddingVertical: 8,
          marginBottom: 6,
          minHeight: 50,
        },
      ]}
    >
      <Text style={{
        fontFamily: 'PressStart2P', fontSize: 8, color: ink, letterSpacing: 1,
      }}>
        WK {String(week.week_number).padStart(2, '0')}
        {week.is_peak && ' [PEAK]'}
        {week.status === 'current' && ' [NOW]'}
      </Text>
      <Text style={{
        fontFamily: 'VT323', fontSize: 14, color: ink, marginTop: 2,
      }}>
        {formatMileageGlyph(week)}
      </Text>
    </Pressable>
  );
}
