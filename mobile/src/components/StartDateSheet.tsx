import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useEffect, useMemo, useState } from 'react';
import { Text, TextInput, View } from 'react-native';

import {
  useResetStartDateApply,
  useResetStartDatePreview,
} from '@/api/hooks/useResetStartDate';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts, radius } from '@/theme/tokens';

const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;

interface Props {
  /** parent passes in today's date as default */
  defaultDate: string;
  onClose: () => void;
  onApplied?: () => void;
}

export const StartDateSheet = forwardRef<BottomSheet, Props>(function StartDateSheet(
  { defaultDate, onClose, onApplied }, ref,
) {
  const snapPoints = useMemo(() => ['75%', '95%'], []);
  const [dateInput, setDateInput] = useState(defaultDate);
  const validDate = ISO_RE.test(dateInput);
  const previewQ = useResetStartDatePreview(validDate ? dateInput : null);
  const applyMut = useResetStartDateApply();

  useEffect(() => {
    setDateInput(defaultDate);
  }, [defaultDate]);

  const submit = () => {
    if (!validDate) return;
    applyMut.mutate(
      { new_start_date: dateInput },
      {
        onSuccess: () => {
          onApplied?.();
          onClose();
        },
      },
    );
  };

  const labelStyle = {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.inkDim,
    marginBottom: 4,
    letterSpacing: 0.5,
  } as const;

  const impact = previewQ.data?.impact;

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
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 22, color: colors.accentHi, marginBottom: 8 }}>
          Reset start date
        </Text>
        <Text style={{ fontFamily: fonts.mono, fontSize: 14, color: colors.inkDim, marginBottom: 18, lineHeight: 20 }}>
          Reseeds the plan from the chosen date. Completed workouts before
          this date stay in your history but drop from the active program.
        </Text>

        <Text style={labelStyle}>NEW START DATE (YYYY-MM-DD)</Text>
        <TextInput
          value={dateInput}
          onChangeText={setDateInput}
          placeholder="2026-05-06"
          placeholderTextColor={colors.inkMute}
          style={{
            fontFamily: fonts.mono,
            fontSize: 16,
            color: colors.ink,
            padding: 8,
            borderWidth: 2,
            borderColor: validDate ? colors.line : colors.accentDanger,
            borderRadius: radius.sm,
            marginBottom: 14,
          }}
        />

        {previewQ.isLoading && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, marginBottom: 10 }}>
            Computing impact…
          </Text>
        )}

        {previewQ.isError && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, marginBottom: 10 }}>
            Could not preview the shift.
          </Text>
        )}

        {impact !== undefined && (
          <RetroBorder background={colors.bgPanelAlt} style={{ marginBottom: 16 }}>
            <View style={{ padding: 14 }}>
              <Text style={{ fontFamily: fonts.monoBold, fontSize: 14, color: colors.ink, marginBottom: 8 }}>
                Impact preview
              </Text>
              <ImpactRow
                label="New cycle 1"
                value={`${impact.new_cycle1_start} → ${impact.new_cycle1_end}`}
                sub={`${impact.new_cycle1_weeks} weeks`}
              />
              <ImpactRow label="Planned workouts dropped" value={String(impact.planned_dropped)} />
              <ImpactRow label="Completed kept" value={String(impact.completed_kept)} />
              {impact.completed_dropped > 0 && (
                <ImpactRow label="Completed dropped" value={String(impact.completed_dropped)} />
              )}
              {impact.proposals_discarded > 0 && (
                <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, marginTop: 8, letterSpacing: 0.5 }}>
                  ! {impact.proposals_discarded} OPEN COACH PROPOSAL{impact.proposals_discarded > 1 ? 'S' : ''} WILL BE DROPPED
                </Text>
              )}
            </View>
          </RetroBorder>
        )}

        {applyMut.isError && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.accentDanger, marginBottom: 10 }}>
            {applyMut.error.message ?? 'Reset failed.'}
          </Text>
        )}

        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
          <View style={{ flex: 1 }}>
            <RetroButton label="Cancel" onPress={onClose} disabled={applyMut.isPending} />
          </View>
          <View style={{ flex: 1 }}>
            <RetroButton
              label={applyMut.isPending ? 'Resetting…' : 'Confirm reset'}
              tone="danger"
              onPress={submit}
              disabled={!validDate || applyMut.isPending}
            />
          </View>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
});

function ImpactRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginVertical: 4 }}>
      <Text style={{ fontFamily: fonts.mono, fontSize: 13, color: colors.inkDim }}>
        {label}
      </Text>
      <View style={{ alignItems: 'flex-end' }}>
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 14, color: colors.ink }}>
          {value}
        </Text>
        {sub !== undefined && (
          <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim }}>
            {sub}
          </Text>
        )}
      </View>
    </View>
  );
}
