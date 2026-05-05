export function formatDistance(miles: number | null | undefined): string {
  if (miles == null) return '—';
  return `${miles.toFixed(1)}mi`;
}

export function formatPace(secondsPerMile: number | null | undefined): string {
  if (secondsPerMile == null) return '—';
  const m = Math.floor(secondsPerMile / 60);
  const s = Math.round(secondsPerMile % 60);
  return `${m}:${String(s).padStart(2, '0')}/mi`;
}

export function formatHrZone(low: number | null, high: number | null): string {
  if (low == null && high == null) return '—';
  if (low != null && high != null) return `${low}-${high} bpm`;
  return `${low ?? high} bpm`;
}

export function titleCase(s: string): string {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}
