import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';

interface SyncReport {
  synced_activities: number;
  synced_metrics: number;
  errors: string[];
}

export function useSync() {
  const qc = useQueryClient();
  return useMutation<SyncReport, Error, void>({
    mutationFn: async () => {
      const res = await api.post<SyncReport>('/admin/sync');
      return res.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workouts', 'recent'] });
      void qc.invalidateQueries({ queryKey: ['garmin'] });
    },
  });
}
