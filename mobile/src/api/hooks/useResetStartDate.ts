import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { StartDateRequest, StartDateResponse } from '@/api/types';

export function useResetStartDatePreview(newStartDate: string | null) {
  return useQuery({
    queryKey: ['plan', 'start-date', 'preview', newStartDate],
    enabled: newStartDate !== null,
    queryFn: async () => {
      const res = await api.post<StartDateResponse>(
        '/plan/start-date',
        { new_start_date: newStartDate } as StartDateRequest,
        { params: { dry_run: true } },
      );
      return res.data;
    },
    staleTime: 0,
  });
}

export function useResetStartDateApply() {
  const qc = useQueryClient();
  return useMutation<StartDateResponse, Error, StartDateRequest>({
    mutationFn: async (body) => {
      const res = await api.post<StartDateResponse>(
        '/plan/start-date',
        body,
      );
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workouts'] });
    },
  });
}
