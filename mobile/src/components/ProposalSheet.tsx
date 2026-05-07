import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import type { AdapterOption, ApplyChoice, ProposalOut } from '@/api/types';
import { RetroBorder } from '@/components/retro/RetroBorder';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts } from '@/theme/tokens';

interface Props {
  proposal: ProposalOut | null;
  submitting: boolean;
  onApply: (choice: ApplyChoice) => Promise<void> | void;
  onCancel: () => Promise<void> | void;
}

function OptionCard({
  option, expanded, onToggle, onApply, disabled,
}: {
  option: AdapterOption;
  expanded: boolean;
  onToggle: () => void;
  onApply: () => void;
  disabled: boolean;
}) {
  return (
    <RetroBorder style={{ marginBottom: 12 }}>
      <View style={{ padding: 14 }}>
        <Text style={{ fontFamily: fonts.monoBold, fontSize: 14, color: colors.ink }}>
          {option.label}
        </Text>
        <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.inkDim, marginTop: 4 }}>
          {option.tradeoff}
        </Text>
        <Pressable onPress={onToggle} hitSlop={6}>
          <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.accentRun, marginTop: 8, letterSpacing: 0.5 }}>
            {expanded ? '▾ Hide' : '▸ Why this'}
          </Text>
        </Pressable>
        {expanded && (
          <Text style={{ fontFamily: fonts.body, fontSize: 16, color: colors.ink, marginTop: 8, lineHeight: 20 }}>
            {option.rationale}
          </Text>
        )}
        <View style={{ marginTop: 12 }}>
          <RetroButton label="Apply" tone="primary" onPress={onApply} disabled={disabled} />
        </View>
      </View>
    </RetroBorder>
  );
}

export const ProposalSheet = forwardRef<BottomSheet, Props>(function ProposalSheet(
  { proposal, submitting, onApply, onCancel }, ref,
) {
  const snapPoints = useMemo(() => ['60%', '92%'], []);
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={() => { if (proposal !== null) void onCancel(); }}
      backgroundStyle={{ backgroundColor: colors.bgPanel, borderTopWidth: 2, borderColor: colors.line, borderRadius: 0 }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {proposal === null ? (
          <View style={{ alignItems: 'center', paddingVertical: 24 }}>
            <ActivityIndicator color={colors.accentRun} />
            <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, marginTop: 12, letterSpacing: 0.5 }}>
              Coach is thinking…
            </Text>
          </View>
        ) : (
          <View>
            <Text style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.inkDim, letterSpacing: 0.5 }}>
              Proposed rebalance
            </Text>
            <Text style={{ fontFamily: fonts.body, fontSize: 22, color: colors.ink, marginTop: 6, marginBottom: 16, lineHeight: 26 }}>
              {proposal.summary}
            </Text>

            {proposal.options.map((option) => (
              <OptionCard
                key={option.id}
                option={option}
                expanded={expanded === option.id}
                onToggle={() => { setExpanded((cur) => (cur === option.id ? null : option.id)); }}
                onApply={() => { void onApply(option.id); }}
                disabled={submitting}
              />
            ))}

            <View style={{ marginTop: 4 }}>
              <RetroButton label="Just move it" onPress={() => { void onApply('just_move'); }} disabled={submitting} />
            </View>
            <View style={{ marginTop: 8 }}>
              <RetroButton label="Cancel" tone="danger" onPress={() => { void onCancel(); }} disabled={submitting} />
            </View>
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
