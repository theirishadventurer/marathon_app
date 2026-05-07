import { Pressable, Text, View } from 'react-native';

import type { WeekRollup } from '@/api/types';
import { colors, fonts, radius } from '@/theme/tokens';
import { softBorder } from '@/theme/retro';

interface Props {
  week: WeekRollup;
  onPress?: () => void;
}

interface Tag {
  label: string;
  bg: string;
  ink: string;
}

const TAG_BY_STATUS: Record<WeekRollup['status'], Tag | null> = {
  done:     { label: 'DONE',  bg: colors.accentRun,    ink: colors.bg },
  partial:  { label: 'PART',  bg: colors.accentDanger, ink: colors.ink },
  current:  { label: 'NOW',   bg: colors.accentHi,     ink: colors.bg },
  upcoming: null,
  skipped:  { label: 'SKIP',  bg: colors.accentDanger, ink: colors.ink },
};

function formatMileageGlyph(week: WeekRollup): string {
  const planned = parseFloat(week.planned_mi);
  const actual = parseFloat(week.actual_mi);
  if (week.has_race) return `[FLAG]`;
  if (week.is_peak) return `★ ${Math.round(planned)}mi`;
  if (week.is_cutback) return `↓ ${Math.round(planned)}mi`;
  if (week.status === 'done' && actual >= planned) return `✓ ${Math.round(actual)}mi`;
  if (week.status === 'done') return `✓ ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  if (week.status === 'current') return `▶ ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  if (week.status === 'partial' || week.status === 'skipped') {
    return `! ${actual.toFixed(1)}/${Math.round(planned)}mi`;
  }
  return `— ${Math.round(planned)}mi`;
}

export function WeekTile({ week, onPress }: Props) {
  const isUpcoming = week.status === 'upcoming';
  const showCutbackBorder = week.is_cutback && !isUpcoming;
  const tag = TAG_BY_STATUS[week.status];
  const titleInk = isUpcoming ? colors.inkDim : colors.ink;

  return (
    <Pressable
      onPress={onPress}
      style={[
        softBorder(showCutbackBorder ? 2 : 1, radius.md),
        {
          backgroundColor: colors.bgPanel,
          borderColor: showCutbackBorder ? colors.accentRest : colors.line,
          paddingHorizontal: 8,
          paddingVertical: 6,
          marginBottom: 6,
          minHeight: 50,
        },
      ]}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
        <Text style={{
          fontFamily: fonts.monoBold, fontSize: 11, color: titleInk, letterSpacing: 0.5,
        }}>
          WK {String(week.week_number).padStart(2, '0')}
        </Text>
        <View style={{ flex: 1 }} />
        {tag !== null && (
          <View style={{
            backgroundColor: tag.bg,
            borderRadius: radius.sm,
            paddingHorizontal: 4,
            paddingVertical: 1,
          }}>
            <Text style={{
              fontFamily: fonts.pixel, fontSize: 7, color: tag.ink, letterSpacing: 0.5,
            }}>
              {tag.label}
            </Text>
          </View>
        )}
        {week.is_peak && (
          <View style={{
            backgroundColor: colors.accentHi,
            borderRadius: radius.sm,
            paddingHorizontal: 4,
            paddingVertical: 1,
          }}>
            <Text style={{
              fontFamily: fonts.pixel, fontSize: 7, color: colors.bg, letterSpacing: 0.5,
            }}>
              PEAK
            </Text>
          </View>
        )}
      </View>
      <Text style={{
        fontFamily: fonts.mono, fontSize: 11, color: isUpcoming ? colors.inkDim : colors.ink, marginTop: 3,
      }}>
        {formatMileageGlyph(week)}
      </Text>
    </Pressable>
  );
}
