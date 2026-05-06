import BottomSheet from '@gorhom/bottom-sheet';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useEditWorkout } from '@/api/hooks/useEditWorkout';
import { useRescheduleOriginal } from '@/api/hooks/useRescheduleOriginal';
import { useApplyMove } from '@/api/hooks/useWorkouts';
import type {
  ApplyChoice,
  EditWorkoutRequest,
  PlannedWorkoutOut,
  PlannedWorkoutSnapshot,
  ProposalOut,
} from '@/api/types';

interface DisplacedState {
  workoutId: string;
  snapshot: PlannedWorkoutSnapshot;
}

interface ProposalState {
  workoutId: string;
  data: ProposalOut;
}

export interface EditFlow {
  // refs
  editRef: React.RefObject<BottomSheet | null>;
  displacedRef: React.RefObject<BottomSheet | null>;
  proposalRef: React.RefObject<BottomSheet | null>;
  // state
  editTarget: PlannedWorkoutOut | null;
  displaced: DisplacedState | null;
  proposal: ProposalState | null;
  editPending: boolean;
  reschedulePending: boolean;
  applyPending: boolean;
  // actions
  openEdit: (w: PlannedWorkoutOut) => void;
  closeEdit: () => void;
  confirmEdit: (body: EditWorkoutRequest) => void;
  pickDisplacedDay: (newDate: string) => void;
  dropDisplaced: () => void;
  applyProposal: (choice: ApplyChoice) => void;
  cancelProposal: () => void;
}

export function useEditFlow(): EditFlow {
  const editRef = useRef<BottomSheet>(null);
  const displacedRef = useRef<BottomSheet>(null);
  const proposalRef = useRef<BottomSheet>(null);

  const [editTarget, setEditTarget] = useState<PlannedWorkoutOut | null>(null);
  const [displaced, setDisplaced] = useState<DisplacedState | null>(null);
  const [proposal, setProposal] = useState<ProposalState | null>(null);

  const editMut = useEditWorkout();
  const reschedMut = useRescheduleOriginal();
  const applyMut = useApplyMove();

  // Open / close sheets in response to state.
  useEffect(() => {
    if (displaced !== null) displacedRef.current?.snapToIndex(0);
    else displacedRef.current?.close();
  }, [displaced]);

  useEffect(() => {
    if (proposal !== null) proposalRef.current?.snapToIndex(0);
    else proposalRef.current?.close();
  }, [proposal]);

  const openEdit = useCallback((w: PlannedWorkoutOut) => {
    setEditTarget(w);
    editRef.current?.snapToIndex(0);
  }, []);

  const closeEdit = useCallback(() => {
    editRef.current?.close();
  }, []);

  const confirmEdit = useCallback((body: EditWorkoutRequest) => {
    if (editTarget === null) return;
    editMut.mutate(
      { workoutId: editTarget.id, body, preEditSnapshot: editTarget.original_snapshot },
      {
        onSuccess: ({ workout, firstEdit }) => {
          editRef.current?.close();
          setEditTarget(null);
          if (firstEdit && workout.original_snapshot !== null) {
            setDisplaced({ workoutId: workout.id, snapshot: workout.original_snapshot });
          }
        },
      },
    );
  }, [editTarget, editMut]);

  const pickDisplacedDay = useCallback((newDate: string) => {
    if (displaced === null) return;
    reschedMut.mutate(
      { workoutId: displaced.workoutId, body: { new_date: newDate } },
      {
        onSuccess: (data) => {
          setDisplaced(null);
          setProposal({ workoutId: data.new_workout_id, data: data.proposal });
        },
      },
    );
  }, [displaced, reschedMut]);

  const dropDisplaced = useCallback(() => {
    setDisplaced(null);
  }, []);

  const applyProposal = useCallback((choice: ApplyChoice) => {
    if (proposal === null) return;
    applyMut.mutate(
      {
        workoutId: proposal.workoutId,
        body: { proposal_id: proposal.data.proposal_id, choice },
      },
      {
        onSuccess: () => {
          setProposal(null);
        },
      },
    );
  }, [proposal, applyMut]);

  const cancelProposal = useCallback(() => {
    applyProposal('cancel');
  }, [applyProposal]);

  return {
    editRef,
    displacedRef,
    proposalRef,
    editTarget,
    displaced,
    proposal,
    editPending: editMut.isPending,
    reschedulePending: reschedMut.isPending,
    applyPending: applyMut.isPending,
    openEdit,
    closeEdit,
    confirmEdit,
    pickDisplacedDay,
    dropDisplaced,
    applyProposal,
    cancelProposal,
  };
}
