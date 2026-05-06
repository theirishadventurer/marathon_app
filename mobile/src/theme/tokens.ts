export const colors = {
  bg: '#0d0d12',
  bgPanel: '#11142a',
  bgPanelAlt: '#1a1d3d',
  bgCard: '#11142a',  // alias kept for backward compat with existing consumers
  bgElev: '#11142a',  // alias
  ink: '#f4f4ec',
  inkDim: '#9a9aab',
  inkMute: '#5a5a6b',
  line: '#000000',
  accentRun: '#5cd86c',
  accentStrength: '#e8a23a',
  accentRest: '#5b8cff',
  accentDanger: '#e84a4a',
  accentHi: '#f7d51d',
} as const;

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32,
} as const;

export const radius = { sm: 0, md: 0, lg: 0, xl: 0 } as const;  // NES = no rounding

export type WorkoutFamily = 'running' | 'strength' | 'other';

export const familyColor: Record<WorkoutFamily, string> = {
  running: colors.accentRun,
  strength: colors.accentStrength,
  other: colors.accentRest,
};

export const fonts = {
  pixel: 'PressStart2P',
  body: 'VT323',
} as const;
