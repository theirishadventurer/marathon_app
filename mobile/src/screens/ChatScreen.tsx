import BottomSheet from '@gorhom/bottom-sheet';
import { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useApplyChatProposal, useChatHistory, useSendChat } from '@/api/hooks/useChat';
import type { ApplyChoice, ChatMessageOut, ProposalOut } from '@/api/types';
import { ChatBubble } from '@/components/ChatBubble';
import { ProposalSheet } from '@/components/ProposalSheet';
import { RetroButton } from '@/components/retro/RetroButton';
import { colors, fonts } from '@/theme/tokens';

export function ChatScreen() {
  const history = useChatHistory();
  const send = useSendChat();
  const applyProposal = useApplyChatProposal();
  const sheetRef = useRef<BottomSheet>(null);

  const [input, setInput] = useState('');
  const [activeProposal, setActiveProposal] = useState<ProposalOut | null>(null);

  const onSend = useCallback(async () => {
    const text = input.trim();
    if (!text || send.isPending) return;
    setInput('');
    const res = await send.mutateAsync(text);
    if (res.proposal) {
      setActiveProposal(res.proposal);
      sheetRef.current?.expand();
    }
  }, [input, send]);

  const onApply = useCallback(
    async (choice: ApplyChoice) => {
      if (!activeProposal) return;
      await applyProposal.mutateAsync({ proposalId: activeProposal.proposal_id, choice });
      setActiveProposal(null);
      sheetRef.current?.close();
    },
    [activeProposal, applyProposal],
  );

  const onCancel = useCallback(async () => {
    if (activeProposal) {
      await applyProposal.mutateAsync({
        proposalId: activeProposal.proposal_id,
        choice: 'cancel',
      });
    }
    setActiveProposal(null);
    sheetRef.current?.close();
  }, [activeProposal, applyProposal]);

  const renderItem = useCallback(
    ({ item }: { item: ChatMessageOut }) => {
      const proposal = item.proposal;
      return (
        <View>
          <ChatBubble role={item.role} contentMd={item.content_md} />
          {proposal && proposal.state === 'pending' && (
            <View style={{ marginHorizontal: 12, marginBottom: 8, alignSelf: 'flex-start' }}>
              <RetroButton
                label="Review proposal"
                tone="primary"
                onPress={() => {
                  setActiveProposal(proposal);
                  sheetRef.current?.expand();
                }}
              />
            </View>
          )}
        </View>
      );
    },
    [],
  );

  return (
    <SafeAreaView className="flex-1 bg-bg" edges={['top']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {history.isLoading ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
            <ActivityIndicator color={colors.accentRun} />
          </View>
        ) : history.isError ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 }}>
            <Text style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.inkDim, textAlign: 'center' }}>
              Couldn{'’'}t load chat. Pull the app down and try again.
            </Text>
          </View>
        ) : (history.data?.messages.length ?? 0) === 0 ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 }}>
            <Text style={{ fontFamily: fonts.body, fontSize: 18, color: colors.inkDim, textAlign: 'center' }}>
              Ask your coach anything — training tweaks, how a workout felt, or what{'’'}s next.
            </Text>
          </View>
        ) : (
          <FlatList
            data={history.data?.messages ?? []}
            keyExtractor={(m) => m.id}
            renderItem={renderItem}
            contentContainerStyle={{ paddingVertical: 12 }}
          />
        )}

        <View
          style={{
            flexDirection: 'row',
            padding: 12,
            borderTopWidth: 2,
            borderColor: colors.line,
            alignItems: 'flex-end',
          }}
        >
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask your coach…"
            placeholderTextColor={colors.inkDim}
            multiline
            style={{
              flex: 1,
              color: colors.ink,
              fontFamily: fonts.body,
              fontSize: 16,
              maxHeight: 120,
              borderWidth: 2,
              borderColor: colors.line,
              padding: 10,
              marginRight: 8,
            }}
          />
          <Pressable
            onPress={() => void onSend()}
            disabled={send.isPending || !input.trim()}
            style={{
              paddingVertical: 12,
              paddingHorizontal: 14,
              backgroundColor: colors.accentRun,
              opacity: send.isPending || !input.trim() ? 0.4 : 1,
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {send.isPending ? (
              <ActivityIndicator color={colors.bg} />
            ) : (
              <Text style={{ color: colors.bg, fontFamily: fonts.pixel, fontSize: 12 }}>{'▸'}</Text>
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <ProposalSheet
        ref={sheetRef}
        proposal={activeProposal}
        submitting={applyProposal.isPending}
        onApply={onApply}
        onCancel={onCancel}
      />
    </SafeAreaView>
  );
}
