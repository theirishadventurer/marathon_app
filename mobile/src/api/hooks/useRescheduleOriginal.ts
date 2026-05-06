import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { RescheduleOriginalRequest, RescheduleOriginalResponse } from '@/api/types';

interface Vars {
  workoutId: string;
  body: RescheduleOriginalRequest;
}

export function useRescheduleOriginal() {
  const qc = useQueryClient();
  return useMutation<RescheduleOriginalResponse, Error, Vars>({
    mutationFn: async ({ workoutId, body }) => {
      const res = await api.post<RescheduleOriginalResponse>(
        `/workouts/${workoutId}/reschedule-original`, body,
      );
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
    },
  });
}
