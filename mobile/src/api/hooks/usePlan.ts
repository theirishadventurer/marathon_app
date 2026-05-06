import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import type {
  PlanCurrentOut, PlanFullOut, PlanStatsOut, TodayOut, WeekOut,
} from '@/api/types';

export function usePlanCurrent() {
  return useQuery({
    queryKey: ['plan', 'current'],
    queryFn: async () => (await api.get<PlanCurrentOut>('/plan/current')).data,
  });
}

export function usePlanToday() {
  return useQuery({
    queryKey: ['plan', 'today'],
    queryFn: async () => (await api.get<TodayOut>('/plan/today')).data,
  });
}

export function usePlanWeek(date?: string) {
  return useQuery({
    queryKey: ['plan', 'week', date ?? 'this'],
    queryFn: async () => {
      const res = await api.get<WeekOut>('/plan/week', {
        params: date !== undefined ? { date } : undefined,
      });
      return res.data;
    },
  });
}

export function usePlanFull() {
  return useQuery({
    queryKey: ['plan', 'full'],
    queryFn: async () => (await api.get<PlanFullOut>('/plan/full')).data,
    staleTime: 60_000,
  });
}

export function useProgressStats(scope: 'cycle' | 'plan' = 'cycle') {
  return useQuery({
    queryKey: ['plan', 'stats', scope],
    queryFn: async () =>
      (await api.get<PlanStatsOut>('/plan/stats', { params: { scope } })).data,
    staleTime: 60_000,
  });
}
