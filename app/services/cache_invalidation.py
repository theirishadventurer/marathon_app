from __future__ import annotations

from uuid import UUID

from app.services.plan_aggregator import invalidate_plan_cache as _invalidate_plan


def invalidate_for_athlete(athlete_id: UUID) -> None:
    """Bust every per-athlete cache.

    Called from any mutation handler that changes athlete-visible state.
    Currently fans out to:
    - plan_aggregator's plan_full + plan_stats caches
    - workouts route's recent-completed cache

    Phase 2 tasks will extend this fan-out as new caches land
    (coach_brief in 2.B2).
    """
    _invalidate_plan(athlete_id)

    # Lazy import: app.routes.workouts imports from this module, so a
    # top-level import here would create a circular dependency at startup.
    from app.routes.workouts import _clear_recent_completed_cache

    _clear_recent_completed_cache(athlete_id)
