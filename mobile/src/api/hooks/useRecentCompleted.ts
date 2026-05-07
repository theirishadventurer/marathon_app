import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { CompletedWorkoutOut } from '@/api/types';

export function useRecentCompleted(limit = 5) {
  return useQuery({
    queryKey: ['workouts', 'recent', limit],
    queryFn: async () =>
      (await api.get<CompletedWorkoutOut[]>('/workouts/completed/recent', {
        params: { limit },
      })).data,
    staleTime: 60_000,
  });
}
