import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';

import type { EditWorkoutRequest, PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts } from '@/theme/tokens';

interface QuickPick {
  type: string;
  label: string;
  family: 'running' | 'strength' | 'other';
  defaultDistanceMi: number | null;
  defaultDurationMin: number | null;
  defaultTitle: string;
  defaultDescriptionMd: string;
  defaultIntentMd: string;
}

const QUICK_PICKS: QuickPick[] = [
  { type: 'easy',       label: 'EASY',     family: 'running',  defaultDistanceMi: 5,    defaultDurationMin: 50,  defaultTitle: 'Easy run',     defaultDescriptionMd: 'Easy aerobic effort, conversational pace.',                           defaultIntentMd: 'Aerobic base / recovery' },
  { type: 'tempo',      label: 'TEMPO',    family: 'running',  defaultDistanceMi: 6,    defaultDurationMin: 55,  defaultTitle: 'Tempo run',    defaultDescriptionMd: 'Tempo effort: controlled, stronger than MP. Hold steady.',           defaultIntentMd: 'Threshold development' },
  { type: 'long',       label: 'LONG',     family: 'running',  defaultDistanceMi: 12,   defaultDurationMin: 120, defaultTitle: 'Long run',     defaultDescriptionMd: 'Long run at conversational pace. Fuel per progression.',             defaultIntentMd: 'Aerobic endurance' },
  { type: 'intervals',  label: 'INTERVAL', family: 'running',  defaultDistanceMi: 6,    defaultDurationMin: 50,  defaultTitle: 'Intervals',    defaultDescriptionMd: 'Interval session at threshold or above. Full recoveries between reps.', defaultIntentMd: 'VO2max / speed' },
  { type: 'strength_a', label: 'STR-A',    family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45,  defaultTitle: 'Strength A',   defaultDescriptionMd: 'Strength A — heavier lower body (squat, RDL, bench, pulls).',         defaultIntentMd: 'Heavy lower strength' },
  { type: 'strength_b', label: 'STR-B',    family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45,  defaultTitle: 'Strength B',   defaultDescriptionMd: 'Strength B — lighter upper + accessories (OH press, split squat, carry).', defaultIntentMd: 'Upper strength + balance' },
  { type: 'cross',      label: 'CROSS',    family: 'other',    defaultDistanceMi: null, defaultDurationMin: 45,  defaultTitle: 'Cross-train',  defaultDescriptionMd: 'Cross-training: bike, row, or swim. Low-impact aerobic.',             defaultIntentMd: 'Cross-training' },
  { type: 'rest',       label: 'REST',     family: 'other',    defaultDistanceMi: null, defaultDurationMin: 0,   defaultTitle: 'Rest',         defaultDescriptionMd: 'Rest day. Mobility or full off.',                                     defaultIntentMd: 'Recovery' },
];

interface Props {
  workout: PlannedWorkoutOut | null;
  submitting: boolean;
  onConfirm: (body: EditWorkoutRequest) => void;
  onClose: () => void;
}

export const EditQuestSheet = forwardRef<BottomSheet, Props>(function EditQuestSheet(
  { workout, submitting, onConfirm, onClose }, ref,
) {
  const snapPoints = useMemo(() => ['70%', '95%'], []);
  const [picked, setPicked] = useState<QuickPick | null>(null);
  // Default open so distance/duration are visible immediately on quick-pick.
  // Previously collapsed-by-default caused users to ship silent defaults.
  const [tweaking, setTweaking] = useState(true);
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [title, setTitle] = useState('');

  const choosePick = (p: QuickPick) => {
    setPicked(p);
    setDistance(p.defaultDistanceMi !== null ? String(p.defaultDistanceMi) : '');
    setDuration(p.defaultDurationMin !== null ? String(p.defaultDurationMin) : '');
    setTitle(p.defaultTitle);
  };

  const submit = () => {
    if (picked === null) return;
    // Include description_md + intent_md from the picked template so the
    // backend stops carrying stale prescription/intent from the prior type.
    const body: EditWorkoutRequest = {
      type: picked.type,
      title,
      description_md: picked.defaultDescriptionMd,
      intent_md: picked.defaultIntentMd,
    };
    const d = parseFloat(distance);
    if (!Number.isNaN(d)) body.distance_mi = d;
    else body.distance_mi = null;
    const m = parseInt(duration, 10);
    if (!Number.isNaN(m)) body.duration_min = m;
    else body.duration_min = null;
    onConfirm(body);
  };

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={onClose}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 18, color: colors.accentHi, marginBottom: 18 }}>
          Edit Quest
        </Text>
        {workout !== null && (
          <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.inkDim, marginBottom: 14 }}>
            currently: {workout.title}
          </Text>
        )}

        <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 8, letterSpacing: 0.5 }}>
          Quick pick
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {QUICK_PICKS.map((p) => {
            const selected = picked?.type === p.type;
            return (
              <Pressable
                key={p.type}
                onPress={() => { choosePick(p); }}
                style={{
                  borderWidth: 2,
                  borderColor: selected ? colors.accentRun : colors.line,
                  backgroundColor: selected ? colors.accentRun : colors.bgPanelAlt,
                  paddingHorizontal: 10,
                  paddingVertical: 8,
                  width: '47%',
                }}
              >
                <Text style={{
                  fontFamily: 'PressStart2P', fontSize: 8,
                  color: selected ? colors.bg : colors.ink,
                  letterSpacing: 1, textAlign: 'center',
                }}>
                  {p.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable onPress={() => { setTweaking((t) => !t); }} hitSlop={6}>
          <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.accentRun, marginBottom: 8, letterSpacing: 0.5 }}>
            {tweaking ? '▾ Hide stats' : '▸ Tweak stats'}
          </Text>
        </Pressable>

        {tweaking && (
          <RetroBorder style={{ marginBottom: 16 }} background={colors.bgPanelAlt}>
            <View style={{ padding: 12 }}>
              <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 4, letterSpacing: 0.5 }}>Distance (mi)</Text>
              <TextInput value={distance} onChangeText={setDistance} keyboardType="decimal-pad"
                style={{ fontFamily: fonts.body, fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 4, letterSpacing: 0.5 }}>Duration (min)</Text>
              <TextInput value={duration} onChangeText={setDuration} keyboardType="number-pad"
                style={{ fontFamily: fonts.body, fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginBottom: 4, letterSpacing: 0.5 }}>Title</Text>
              <TextInput value={title} onChangeText={setTitle}
                style={{ fontFamily: fonts.body, fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line }} />
            </View>
          </RetroBorder>
        )}

        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
          <View style={{ flex: 1 }}>
            <RetroButton label="Cancel" onPress={onClose} disabled={submitting} />
          </View>
          <View style={{ flex: 1 }}>
            <RetroButton label="Confirm" tone="primary" onPress={submit} disabled={submitting || picked === null} />
          </View>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
