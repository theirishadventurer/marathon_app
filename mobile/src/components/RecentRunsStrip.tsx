import { Pressable, ScrollView, Text, View } from 'react-native';

import type { CompletedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { fromIso } from '@/lib/dates';
import { colors, fonts, radius } from '@/theme/tokens';

interface Props {
  runs: CompletedWorkoutOut[];
  onPress?: (run: CompletedWorkoutOut) => void;
}

const _METERS_PER_MILE = 1609.344;

function formatDateGlyph(iso: string): string {
  const d = fromIso(iso);
  const dayName = d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
  return `${dayName} ${d.getMonth() + 1}/${d.getDate()}`;
}

function metersToMiles(m: string | null): number | null {
  if (m === null) return null;
  const v = parseFloat(m);
  if (Number.isNaN(v)) return null;
  return v / _METERS_PER_MILE;
}

function deriveAvgPaceMmSsPerMile(distance_m: string | null, duration_s: number): string | null {
  const mi = metersToMiles(distance_m);
  if (mi === null || mi <= 0 || duration_s <= 0) return null;
  const sPerMile = Math.round(duration_s / mi);
  const m = Math.floor(sPerMile / 60);
  const s = sPerMile % 60;
  return `${m}:${String(s).padStart(2, '0')}/mi`;
}

export function RecentRunsStrip({ runs, onPress }: Props) {
  if (runs.length === 0) {
    return (
      <RetroBorder>
        <View style={{ padding: 14 }}>
          <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim }}>
            No recent runs yet. Sync from Garmin or mark a workout done.
          </Text>
        </View>
      </RetroBorder>
    );
  }

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: 4, gap: 10 }}
    >
      {runs.map((r) => {
        const mi = metersToMiles(r.distance_m);
        const pace = deriveAvgPaceMmSsPerMile(r.distance_m, r.duration_s);
        return (
          <Pressable key={r.id} onPress={() => { onPress?.(r); }}>
            <View
              style={{
                width: 140,
                padding: 12,
                backgroundColor: colors.bgPanelAlt,
                borderRadius: radius.md,
                borderWidth: 1,
                borderColor: colors.line,
              }}
            >
              <Text
                style={{
                  fontFamily: fonts.mono,
                  fontSize: 11,
                  color: colors.inkDim,
                  letterSpacing: 0.5,
                  marginBottom: 6,
                }}
              >
                {formatDateGlyph(r.activity_date)}
              </Text>
              <Text style={{ fontFamily: fonts.monoBold, fontSize: 18, color: colors.ink }}>
                {mi !== null ? `${mi.toFixed(1)}mi` : '—'}
              </Text>
              {pace !== null && (
                <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginTop: 2 }}>
                  {pace}
                </Text>
              )}
              {r.avg_hr !== null && (
                <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginTop: 2 }}>
                  {r.avg_hr} bpm
                </Text>
              )}
            </View>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}
