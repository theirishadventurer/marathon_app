import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';

import type { EditWorkoutRequest, PlannedWorkoutOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors } from '@/theme/tokens';

interface QuickPick {
  type: string;
  label: string;
  family: 'running' | 'strength' | 'other';
  defaultDistanceMi: number | null;
  defaultDurationMin: number | null;
  defaultTitle: string;
}

const QUICK_PICKS: QuickPick[] = [
  { type: 'easy', label: 'EASY',     family: 'running',  defaultDistanceMi: 5,  defaultDurationMin: 50,  defaultTitle: 'Easy run' },
  { type: 'tempo', label: 'TEMPO',   family: 'running',  defaultDistanceMi: 6,  defaultDurationMin: 55,  defaultTitle: 'Tempo run' },
  { type: 'long', label: 'LONG',     family: 'running',  defaultDistanceMi: 12, defaultDurationMin: 120, defaultTitle: 'Long run' },
  { type: 'intervals', label: 'INTERVAL', family: 'running', defaultDistanceMi: 6, defaultDurationMin: 50, defaultTitle: 'Intervals' },
  { type: 'strength_a', label: 'STR-A', family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Strength A' },
  { type: 'strength_b', label: 'STR-B', family: 'strength', defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Strength B' },
  { type: 'cross', label: 'CROSS',   family: 'other',    defaultDistanceMi: null, defaultDurationMin: 45, defaultTitle: 'Cross-train' },
  { type: 'rest', label: 'REST',     family: 'other',    defaultDistanceMi: null, defaultDurationMin: 0,  defaultTitle: 'Rest' },
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
  const [tweaking, setTweaking] = useState(false);
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
    const body: EditWorkoutRequest = { type: picked.type, title };
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
        <Text style={{ fontFamily: 'PressStart2P', fontSize: 14, color: colors.accentHi, marginBottom: 14, letterSpacing: 1 }}>
          EDIT QUEST
        </Text>
        {workout !== null && (
          <Text style={{ fontFamily: 'VT323', fontSize: 16, color: colors.inkDim, marginBottom: 14 }}>
            currently: {workout.title}
          </Text>
        )}

        <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 8, letterSpacing: 1 }}>
          QUICK PICK
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
          <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.accentRun, marginBottom: 8, letterSpacing: 1 }}>
            {tweaking ? '▾ HIDE STATS' : '▸ TWEAK STATS'}
          </Text>
        </Pressable>

        {tweaking && (
          <RetroBorder style={{ marginBottom: 16 }} background={colors.bgPanelAlt}>
            <View style={{ padding: 12 }}>
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4, letterSpacing: 1 }}>DISTANCE (MI)</Text>
              <TextInput value={distance} onChangeText={setDistance} keyboardType="decimal-pad"
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4, letterSpacing: 1 }}>DURATION (MIN)</Text>
              <TextInput value={duration} onChangeText={setDuration} keyboardType="number-pad"
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line, marginBottom: 10 }} />
              <Text style={{ fontFamily: 'PressStart2P', fontSize: 8, color: colors.inkDim, marginBottom: 4, letterSpacing: 1 }}>TITLE</Text>
              <TextInput value={title} onChangeText={setTitle}
                style={{ fontFamily: 'VT323', fontSize: 18, color: colors.ink, padding: 6, borderWidth: 2, borderColor: colors.line }} />
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
