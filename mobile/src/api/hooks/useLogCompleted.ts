import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { LogCompletedRequest, LogCompletedResponse } from '@/api/types';

interface Vars {
  workoutId: string;
  body: LogCompletedRequest;
}

export function useLogCompleted() {
  const qc = useQueryClient();
  return useMutation<LogCompletedResponse, Error, Vars>({
    mutationFn: async ({ workoutId, body }) => {
      const res = await api.post<LogCompletedResponse>(
        `/workouts/${workoutId}/log-completed`, body,
      );
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workout'] });
      void qc.invalidateQueries({ queryKey: ['workouts', 'recent'] });
    },
  });
}
