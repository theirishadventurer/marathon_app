from uuid import uuid4


def test_invalidate_for_athlete_clears_plan_full_cache():
    from app.services import plan_aggregator
    from app.services.cache_invalidation import invalidate_for_athlete

    athlete_id = uuid4()
    # Seed the cache
    plan_aggregator._PLAN_FULL_CACHE[athlete_id] = (0.0, "sentinel")  # type: ignore[assignment]
    invalidate_for_athlete(athlete_id)
    assert athlete_id not in plan_aggregator._PLAN_FULL_CACHE


def test_invalidate_for_athlete_clears_plan_stats_cache():
    from app.services import plan_aggregator
    from app.services.cache_invalidation import invalidate_for_athlete

    athlete_id = uuid4()
    plan_aggregator._PLAN_STATS_CACHE[(athlete_id, "cycle")] = (0.0, "sentinel")  # type: ignore[assignment]
    plan_aggregator._PLAN_STATS_CACHE[(athlete_id, "plan")] = (0.0, "sentinel")  # type: ignore[assignment]
    other = uuid4()
    plan_aggregator._PLAN_STATS_CACHE[(other, "cycle")] = (0.0, "sentinel")  # type: ignore[assignment]
    invalidate_for_athlete(athlete_id)
    assert (athlete_id, "cycle") not in plan_aggregator._PLAN_STATS_CACHE
    assert (athlete_id, "plan") not in plan_aggregator._PLAN_STATS_CACHE
    assert (other, "cycle") in plan_aggregator._PLAN_STATS_CACHE  # other athletes untouched
