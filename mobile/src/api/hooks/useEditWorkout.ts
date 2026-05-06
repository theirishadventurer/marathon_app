import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import type { EditWorkoutRequest, PlannedWorkoutOut } from '@/api/types';

interface Vars {
  workoutId: string;
  body: EditWorkoutRequest;
  /** the workout's original_snapshot BEFORE this edit, so the caller can
   *  detect a null→non-null transition (the "first edit" signal) */
  preEditSnapshot: PlannedWorkoutOut['original_snapshot'];
}

interface Result {
  workout: PlannedWorkoutOut;
  /** true iff this PATCH transitioned original_snapshot from null to non-null */
  firstEdit: boolean;
}

export function useEditWorkout() {
  const qc = useQueryClient();
  return useMutation<Result, Error, Vars>({
    mutationFn: async ({ workoutId, body, preEditSnapshot }) => {
      const res = await api.patch<PlannedWorkoutOut>(`/workouts/${workoutId}`, body);
      const firstEdit = preEditSnapshot === null && res.data.original_snapshot !== null;
      return { workout: res.data, firstEdit };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['plan'] });
      void qc.invalidateQueries({ queryKey: ['workout'] });
    },
  });
}
