export const colors = {
  bg: '#0b0b0d',
  bgElev: '#16161a',
  bgCard: '#1c1c22',
  ink: '#f5f5f7',
  inkDim: '#a1a1aa',
  inkMute: '#6b7280',
  line: '#2a2a31',
  accentRun: '#34d399',
  accentStrength: '#f59e0b',
  accentRest: '#60a5fa',
  accentDanger: '#ef4444',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
} as const;

export type WorkoutFamily = 'running' | 'strength' | 'other';

export const familyColor: Record<WorkoutFamily, string> = {
  running: colors.accentRun,
  strength: colors.accentStrength,
  other: colors.accentRest,
};
