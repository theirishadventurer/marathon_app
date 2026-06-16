import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type {
  ApplyChoice,
  ChatHistoryOut,
  PostChatResponse,
} from '@/api/types';

export function useChatHistory() {
  return useQuery({
    queryKey: ['chat', 'history'],
    queryFn: async () => (await api.get<ChatHistoryOut>('/chat')).data,
  });
}

export function useSendChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post<PostChatResponse>('/chat', { message });
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['chat', 'history'] });
    },
  });
}

export function useApplyChatProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { proposalId: string; choice: ApplyChoice }) => {
      await api.post('/chat/proposal/apply', {
        proposal_id: vars.proposalId,
        choice: vars.choice,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['chat', 'history'] });
    },
  });
}
