import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { DailyMetricOut } from '@/api/types';

export function useMetricsRecent(days = 14) {
  return useQuery({
    queryKey: ['metrics', 'recent', days],
    queryFn: async () =>
      (await api.get<DailyMetricOut[]>('/metrics/recent', { params: { days } })).data,
  });
}
