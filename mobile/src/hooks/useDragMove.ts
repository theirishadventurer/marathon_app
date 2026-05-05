import { useQueryClient, type QueryKey } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { useApplyMove, useMoveWorkout } from '@/api/hooks/useWorkouts';
import type { ApplyChoice, IsoDate, PlannedWorkoutOut, ProposalOut, WeekOut } from '@/api/types';

interface PendingMove {
  workoutId: string;
  fromDate: IsoDate;
  toDate: IsoDate;
}

interface DragMoveState {
  proposal: ProposalOut | null;
  submitting: boolean;
  pending: PendingMove | null;
  requestMove: (workout: PlannedWorkoutOut, newDate: IsoDate) => Promise<void>;
  apply: (choice: ApplyChoice) => Promise<void>;
  cancel: () => Promise<void>;
}

function moveWorkoutInWeek(week: WeekOut, workoutId: string, toDate: IsoDate): WeekOut {
  let moved: PlannedWorkoutOut | null = null;
  const stripped = week.days.map((day) => ({
    ...day,
    workouts: day.workouts.filter((w) => {
      if (w.id === workoutId) {
        moved = { ...w, scheduled_date: toDate, status: 'moved' };
        return false;
      }
      return true;
    }),
  }));
  if (moved === null) return week;
  return {
    ...week,
    days: stripped.map((day) =>
      day.date === toDate
        ? { ...day, workouts: [...day.workouts, moved as PlannedWorkoutOut] }
        : day,
    ),
  };
}

export function useDragMove(): DragMoveState {
  const qc = useQueryClient();
  const moveMut = useMoveWorkout();
  const applyMut = useApplyMove();
  const [proposal, setProposal] = useState<ProposalOut | null>(null);
  const [pending, setPending] = useState<PendingMove | null>(null);

  const requestMove = useCallback(
    async (workout: PlannedWorkoutOut, newDate: IsoDate) => {
      if (workout.scheduled_date === newDate) return;

      const weekQueries = qc.getQueriesData<WeekOut>({ queryKey: ['plan', 'week'] });
      const snapshot: Array<readonly [QueryKey, WeekOut | undefined]> = weekQueries.map(
        ([key, data]) => [key as QueryKey, data] as const,
      );

      // optimistic update on every cached week
      for (const [key, data] of weekQueries) {
        if (data === undefined) continue;
        qc.setQueryData(key, moveWorkoutInWeek(data, workout.id, newDate));
      }

      setPending({
        workoutId: workout.id,
        fromDate: workout.scheduled_date,
        toDate: newDate,
      });

      try {
        const data = await moveMut.mutateAsync({
          workoutId: workout.id,
          body: { new_date: newDate },
        });
        setProposal(data);
      } catch (e) {
        // rollback optimistic state
        for (const [key, data] of snapshot) {
          qc.setQueryData(key, data);
        }
        setPending(null);
        throw e;
      }
    },
    [qc, moveMut],
  );

  const apply = useCallback(
    async (choice: ApplyChoice) => {
      if (proposal === null || pending === null) return;
      await applyMut.mutateAsync({
        workoutId: pending.workoutId,
        body: { proposal_id: proposal.proposal_id, choice },
      });
      setProposal(null);
      setPending(null);
      void qc.invalidateQueries({ queryKey: ['plan'] });
    },
    [proposal, pending, applyMut, qc],
  );

  const cancel = useCallback(async () => {
    if (pending === null) {
      setProposal(null);
      return;
    }
    if (proposal !== null) {
      try {
        await applyMut.mutateAsync({
          workoutId: pending.workoutId,
          body: { proposal_id: proposal.proposal_id, choice: 'cancel' },
        });
      } catch {
        // even if cancel call fails, we still want to roll back UI
      }
    }
    // rollback optimistic update by invalidating week queries (server has fromDate)
    setProposal(null);
    setPending(null);
    void qc.invalidateQueries({ queryKey: ['plan'] });
  }, [pending, proposal, applyMut, qc]);

  return {
    proposal,
    submitting: applyMut.isPending,
    pending,
    requestMove,
    apply,
    cancel,
  };
}
