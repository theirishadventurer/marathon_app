import BottomSheet from '@gorhom/bottom-sheet';
import { useCallback, useRef, useState } from 'react';

import { useLinkCandidates, useLinkCompleted } from '@/api/hooks/useWorkouts';
import type { PlannedWorkoutOut } from '@/api/types';

export interface LinkFlow {
  sheetRef: React.RefObject<BottomSheet | null>;
  target: PlannedWorkoutOut | null;
  submitting: boolean;
  open: (w: PlannedWorkoutOut) => void;
  close: () => void;
  confirm: (completedId: string) => void;
  candidatesData: ReturnType<typeof useLinkCandidates>['data'];
  candidatesLoading: boolean;
}

export function useLinkFlow(): LinkFlow {
  const sheetRef = useRef<BottomSheet>(null);
  const [target, setTarget] = useState<PlannedWorkoutOut | null>(null);
  const [open, setOpen] = useState(false);
  const linkMut = useLinkCompleted();
  const { data: candidatesData, isLoading: candidatesLoading } = useLinkCandidates(
    target?.id ?? null,
    open,
  );

  const openSheet = useCallback((w: PlannedWorkoutOut) => {
    setTarget(w);
    setOpen(true);
    sheetRef.current?.snapToIndex(0);
  }, []);

  const close = useCallback(() => {
    sheetRef.current?.close();
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
    setTarget(null);
  }, []);

  const confirm = useCallback((completedId: string) => {
    if (target === null) return;
    linkMut.mutate(
      { workoutId: target.id, body: { completed_id: completedId } },
      {
        onSuccess: () => {
          sheetRef.current?.close();
          setOpen(false);
          setTarget(null);
        },
      },
    );
  }, [target, linkMut]);

  return {
    sheetRef,
    target,
    submitting: linkMut.isPending,
    open: openSheet,
    close: handleClose,
    confirm,
    candidatesData,
    candidatesLoading,
  };
}
