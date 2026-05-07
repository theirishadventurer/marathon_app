import { Pressable, Text, View } from 'react-native';

import type { PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroPill } from '@/components/retro/RetroPill';
import { formatDistance } from '@/lib/format';
import { dayName, fromIso } from '@/lib/dates';
import { colors, fonts, type WorkoutFamily } from '@/theme/tokens';

const FAMILIES: ReadonlySet<WorkoutFamily> = new Set(['running', 'strength', 'other']);

function asFamily(raw: string): WorkoutFamily {
  return FAMILIES.has(raw as WorkoutFamily) ? (raw as WorkoutFamily) : 'other';
}

interface FamilyBadge {
  label: string;
  bg: string;
  ink: string;
}

const FAMILY_BADGE: Record<WorkoutFamily, FamilyBadge> = {
  running:  { label: 'RUN',   bg: colors.accentRun,         ink: colors.bg },
  strength: { label: 'STR',   bg: colors.accentStrength,    ink: colors.ink },
  other:    { label: 'CROSS', bg: colors.accentBadgePurple, ink: colors.ink },
};

interface StatusBadge {
  label: string;
  bg: string;
  ink: string;
}

const STATUS_BADGE: Record<PlannedWorkoutOut['status'], StatusBadge | null> = {
  planned: null,
  done:    { label: 'DONE',  bg: 'transparent',         ink: colors.accentRun },
  skipped: { label: 'SKIP',  bg: colors.accentDanger,   ink: colors.ink },
  moved:   { label: 'MOVED', bg: 'transparent',         ink: colors.accentCyan },
};

interface Props {
  workout: PlannedWorkoutOut;
  onPress?: () => void;
  /** Compact composition for narrow contexts (e.g. Program tab cycle lanes). */
  dense?: boolean;
}

function firstSentence(md: string, max = 90): string {
  const trimmed = md.trim();
  if (trimmed.length === 0) return '';
  const firstStop = trimmed.search(/[.!]/);
  const chunk = firstStop === -1 ? trimmed : trimmed.slice(0, firstStop + 1);
  if (chunk.length <= max) return chunk;
  return `${chunk.slice(0, max - 1).trimEnd()}…`;
}

function metaLabel(workout: PlannedWorkoutOut, dense: boolean): string {
  const d = fromIso(workout.scheduled_date);
  const dn = dayName(d).toUpperCase();
  if (dense) {
    return `WK${workout.week_number} · ${dn}`;
  }
  return `${dn} ${d.getMonth() + 1}/${d.getDate()}`;
}

function titleText(workout: PlannedWorkoutOut): string {
  const family = asFamily(workout.family);
  if (family !== 'running' || workout.distance_mi === null) return workout.title;
  const mi = parseFloat(workout.distance_mi);
  if (Number.isNaN(mi)) return workout.title;
  return `${workout.title} · ${formatDistance(mi)}`;
}

/**
 * Staycation-composition workout card. Tap target only — actions
 * (Why, Edit, Mark Done, Skip) live on WorkoutDetail.
 *
 * Composition: meta line + family badge + (status badge?) + chevron;
 * monoBold title; lighter mono sub (first sentence of intent_md).
 *
 * Spec: docs/superpowers/specs/2026-05-07-feat-staycation-ux-overhaul-design.md §5.2.
 */
export function WorkoutCard({ workout, onPress, dense = false }: Props) {
  const family = asFamily(workout.family);
  const fam = FAMILY_BADGE[family];
  const status = STATUS_BADGE[workout.status];
  const wasOriginal = workout.original_snapshot;
  const sub = firstSentence(workout.intent_md);

  const px = dense ? 10 : 14;
  const py = dense ? 8 : 12;
  const titleSize = dense ? 13 : 18;
  const titleLh = dense ? 18 : 24;
  const subSize = dense ? 11 : 14;
  const subLh = dense ? 16 : 20;
  const metaSize = dense ? 10 : 11;
  const subLines = dense ? 1 : 2;

  return (
    <Pressable onPress={onPress} style={{ marginBottom: dense ? 6 : 12 }}>
      <RetroBorder>
        <View style={{ paddingHorizontal: px, paddingVertical: py }}>
          {wasOriginal !== null && (
            <Text style={{
              fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 4,
            }}>
              ↻ was: {wasOriginal.title}
            </Text>
          )}
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: dense ? 2 : 4, gap: 8 }}>
            <Text style={{
              fontFamily: fonts.mono, fontSize: metaSize, color: colors.inkDim, letterSpacing: 0.5,
            }}>
              {metaLabel(workout, dense)}
            </Text>
            <RetroPill variant="badge" label={fam.label} background={fam.bg} color={fam.ink} />
            {status !== null && (
              status.bg === 'transparent' ? (
                <RetroPill variant="bracket" label={status.label} color={status.ink} />
              ) : (
                <RetroPill variant="badge" label={status.label} background={status.bg} color={status.ink} />
              )
            )}
            <View style={{ flex: 1 }} />
            <Text style={{
              fontFamily: fonts.mono, fontSize: dense ? 14 : 18, color: colors.accentCyan,
            }}>
              ›
            </Text>
          </View>
          <Text
            style={{
              fontFamily: fonts.monoBold, fontSize: titleSize, color: colors.ink, lineHeight: titleLh,
            }}
            numberOfLines={dense ? 1 : 2}
          >
            {titleText(workout)}
          </Text>
          {sub.length > 0 && (
            <Text
              style={{
                fontFamily: fonts.mono, fontSize: subSize, color: colors.inkDim, lineHeight: subLh, marginTop: 2,
              }}
              numberOfLines={subLines}
            >
              {sub}
            </Text>
          )}
        </View>
      </RetroBorder>
    </Pressable>
  );
}
