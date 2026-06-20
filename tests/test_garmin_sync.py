def test_map_activity_maps_core_fields():
    from app.services.garmin_sync import map_activity
    act = {
        "activityId": 555,
        "startTimeLocal": "2026-06-10 07:30:00",
        "activityType": {"typeKey": "running"},
        "duration": 1800,
        "distance": 5000,
        "averageHR": 150,
        "maxHR": 170,
    }
    w = map_activity(act, "11111111-1111-1111-1111-111111111111")
    assert w is not None
    assert w.garmin_activity_id == 555
    assert w.source == "garmin"
    assert w.duration_s == 1800


def test_map_activity_returns_none_when_malformed():
    from app.services.garmin_sync import map_activity
    assert map_activity({"startTimeLocal": "2026-06-10 07:30:00"}, "x") is None  # no activityId


def test_map_metric_returns_none_without_calendar_date():
    from app.services.garmin_sync import map_metric
    assert map_metric({"sleepScore": 80}, "x") is None
