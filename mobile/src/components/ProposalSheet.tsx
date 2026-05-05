import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { forwardRef, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import type { AdapterOption, ApplyChoice, ProposalOut } from '@/api/types';
import { colors } from '@/theme/tokens';

interface Props {
  proposal: ProposalOut | null;
  submitting: boolean;
  onApply: (choice: ApplyChoice) => Promise<void> | void;
  onCancel: () => Promise<void> | void;
}

function OptionCard({
  option,
  expanded,
  onToggle,
  onApply,
  disabled,
}: {
  option: AdapterOption;
  expanded: boolean;
  onToggle: () => void;
  onApply: () => void;
  disabled: boolean;
}) {
  return (
    <View
      style={{
        backgroundColor: colors.bgCard,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: colors.line,
        padding: 14,
        marginBottom: 12,
      }}
    >
      <Text style={{ color: colors.ink, fontSize: 16, fontWeight: '700' }}>
        {option.label}
      </Text>
      <Text style={{ color: colors.inkDim, fontSize: 13, marginTop: 4 }}>
        {option.tradeoff}
      </Text>
      <Pressable onPress={onToggle} hitSlop={6}>
        <Text style={{ color: colors.accentRun, fontSize: 12, marginTop: 8 }}>
          {expanded ? 'Hide rationale' : 'Why this option'}
        </Text>
      </Pressable>
      {expanded && (
        <Text style={{ color: colors.ink, fontSize: 13, marginTop: 8, lineHeight: 19 }}>
          {option.rationale}
        </Text>
      )}
      <Pressable
        onPress={onApply}
        disabled={disabled}
        style={{
          backgroundColor: colors.accentRun,
          borderRadius: 8,
          paddingVertical: 10,
          alignItems: 'center',
          marginTop: 12,
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <Text style={{ color: colors.bg, fontWeight: '700' }}>Apply</Text>
      </Pressable>
    </View>
  );
}

export const ProposalSheet = forwardRef<BottomSheet, Props>(function ProposalSheet(
  { proposal, submitting, onApply, onCancel },
  ref,
) {
  const snapPoints = useMemo(() => ['60%', '92%'], []);
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={snapPoints}
      enablePanDownToClose
      onClose={() => {
        if (proposal !== null) {
          void onCancel();
        }
      }}
      backgroundStyle={{ backgroundColor: colors.bgElev }}
      handleIndicatorStyle={{ backgroundColor: colors.inkDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        {proposal === null ? (
          <View style={{ alignItems: 'center', paddingVertical: 24 }}>
            <ActivityIndicator color={colors.accentRun} />
            <Text style={{ color: colors.inkDim, marginTop: 12 }}>
              Coach is thinking…
            </Text>
          </View>
        ) : (
          <View>
            <Text style={{ color: colors.inkDim, fontSize: 12, textTransform: 'uppercase' }}>
              Proposed rebalance
            </Text>
            <Text style={{ color: colors.ink, fontSize: 18, fontWeight: '700', marginTop: 4, marginBottom: 16, lineHeight: 24 }}>
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

            <Pressable
              onPress={() => { void onApply('just_move'); }}
              disabled={submitting}
              style={{
                borderColor: colors.line,
                borderWidth: 1,
                borderRadius: 10,
                paddingVertical: 12,
                alignItems: 'center',
                marginTop: 4,
                opacity: submitting ? 0.5 : 1,
              }}
            >
              <Text style={{ color: colors.ink, fontWeight: '600' }}>Just move it</Text>
              <Text style={{ color: colors.inkDim, fontSize: 12, marginTop: 2 }}>
                Override the AI; no rebalance
              </Text>
            </Pressable>

            <Pressable
              onPress={() => { void onCancel(); }}
              disabled={submitting}
              style={{
                paddingVertical: 12,
                alignItems: 'center',
                marginTop: 8,
                opacity: submitting ? 0.5 : 1,
              }}
            >
              <Text style={{ color: colors.accentDanger, fontWeight: '600' }}>Cancel</Text>
            </Pressable>
          </View>
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
