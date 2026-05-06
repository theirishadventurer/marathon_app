import { View } from 'react-native';

import type { PlanCurrentOut, PlanStatsOut } from '@/api/types';
import { StatTile } from '@/components/program/StatTile';

interface Props {
  stats: PlanStatsOut;
  plan: PlanCurrentOut;
}

function formatPct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function formatDelta(planned: number, actual: number): string {
  return `${actual.toFixed(1)} / ${Math.round(planned)} mi`;
}

export function StatsPanel({ stats, plan }: Props) {
  const cycleProgress = plan.cycle_progress;
  const milestone = stats.next_milestone;
  return (
    <View>
      <View style={{ flexDirection: 'row', marginBottom: 8 }}>
        <StatTile
          label="On-plan"
          value={formatPct(stats.on_plan_pct)}
          sub={`${stats.done_count} done · ${stats.skipped_count} skipped`}
        />
        <StatTile
          label="Cycle"
          value={formatDelta(parseFloat(stats.planned_mi), parseFloat(stats.actual_mi))}
        />
        <StatTile
          label="Streak"
          value={`${stats.streak_days}d`}
        />
      </View>
      <View style={{ flexDirection: 'row' }}>
        <StatTile
          label="Next milestone"
          value={milestone?.label ?? '—'}
          sub={milestone !== null ? milestone.date : undefined}
          flex={2}
        />
        <StatTile
          label="Progress"
          value={cycleProgress !== null ? `WK ${cycleProgress.week} / ${cycleProgress.total_weeks}` : '—'}
          sub={cycleProgress !== null ? `${cycleProgress.days_to_race}d to race` : undefined}
          flex={2}
        />
      </View>
    </View>
  );
}
