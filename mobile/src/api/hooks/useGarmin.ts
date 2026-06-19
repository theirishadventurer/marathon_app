import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { GarminReauthRequest, GarminStatusOut, SyncReportOut } from '@/api/types';

export function useGarminStatus() {
  return useQuery({
    queryKey: ['garmin', 'status'],
    queryFn: async () => (await api.get<GarminStatusOut>('/garmin/status')).data,
  });
}

export function useGarminReauth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: GarminReauthRequest) => {
      await api.post('/garmin/reauth', body);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['garmin'] });
    },
  });
}

export function useManualSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await api.post<SyncReportOut>('/admin/sync')).data,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['garmin'] });
      void qc.invalidateQueries({ queryKey: ['plan'] });
    },
  });
}

export function useRequestSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post('/garmin/request-sync');
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['garmin'] });
    },
  });
}
