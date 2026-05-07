import BottomSheet from '@gorhom/bottom-sheet';
import { useCallback, useRef, useState } from 'react';

import { useLogCompleted } from '@/api/hooks/useLogCompleted';
import { useSync } from '@/api/hooks/useSync';
import type { LogCompletedRequest, PlannedWorkoutOut } from '@/api/types';

export interface LogFlow {
  sheetRef: React.RefObject<BottomSheet | null>;
  target: PlannedWorkoutOut | null;
  submitting: boolean;
  syncPending: boolean;
  open: (w: PlannedWorkoutOut) => void;
  close: () => void;
  confirm: (body: LogCompletedRequest) => void;
  triggerSync: () => void;
}

export function useLogFlow(): LogFlow {
  const sheetRef = useRef<BottomSheet>(null);
  const [target, setTarget] = useState<PlannedWorkoutOut | null>(null);
  const logMut = useLogCompleted();
  const syncMut = useSync();

  const open = useCallback((w: PlannedWorkoutOut) => {
    setTarget(w);
    sheetRef.current?.snapToIndex(0);
  }, []);

  const close = useCallback(() => {
    sheetRef.current?.close();
  }, []);

  const confirm = useCallback((body: LogCompletedRequest) => {
    if (target === null) return;
    logMut.mutate(
      { workoutId: target.id, body },
      {
        onSuccess: () => {
          sheetRef.current?.close();
          setTarget(null);
        },
      },
    );
  }, [target, logMut]);

  const triggerSync = useCallback(() => {
    syncMut.mutate();
  }, [syncMut]);

  return {
    sheetRef,
    target,
    submitting: logMut.isPending,
    syncPending: syncMut.isPending,
    open,
    close,
    confirm,
    triggerSync,
  };
}
