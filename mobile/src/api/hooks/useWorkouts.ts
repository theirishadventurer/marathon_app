import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type {
  ApplyMoveRequest,
  MoveRequest,
  ProposalOut,
  WorkoutDetailOut,
} from '@/api/types';

export function useWorkoutDetail(workoutId: string | null) {
  return useQuery({
    queryKey: ['workout', workoutId],
    enabled: workoutId !== null,
    queryFn: async () =>
      (await api.get<WorkoutDetailOut>(`/workouts/${workoutId}`)).data,
  });
}

export function useSkipWorkout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (workoutId: string) => {
      await api.patch(`/workouts/${workoutId}/skip`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workout'] });
    },
  });
}

export function useMoveWorkout() {
  return useMutation({
    mutationFn: async (vars: { workoutId: string; body: MoveRequest }) => {
      const res = await api.patch<ProposalOut>(
        `/workouts/${vars.workoutId}/move`,
        vars.body,
      );
      return res.data;
    },
  });
}

export function useApplyMove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { workoutId: string; body: ApplyMoveRequest }) => {
      await api.post(`/workouts/${vars.workoutId}/apply-move`, vars.body);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workout'] });
    },
  });
}
