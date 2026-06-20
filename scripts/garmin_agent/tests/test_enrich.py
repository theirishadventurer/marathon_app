from garmin_agent.garmin_fetch import enrich_metric


class FakeClient:
    """Stub returning the real Garmin payload shapes observed in the live
    smoke-test. Any endpoint can be set to raise to test failure isolation."""

    def __init__(self, raise_on=()):
        self.raise_on = set(raise_on)

    def _maybe_raise(self, name):
        if name in self.raise_on:
            raise RuntimeError(f"{name} boom")

    def get_sleep_data(self, cdate):
        self._maybe_raise("get_sleep_data")
        return {
            "avgOvernightHrv": 43.0,
            "restingHeartRate": 64,
            "dailySleepDTO": {
                "sleepTimeSeconds": 22620,
                "sleepScores": {"overall": {"value": 73, "qualifierKey": "FAIR"}},
            },
        }

    def get_training_readiness(self, cdate):
        self._maybe_raise("get_training_readiness")
        return [{"calendarDate": cdate, "score": 40, "level": "LOW"}]

    def get_training_status(self, cdate):
        self._maybe_raise("get_training_status")
        return {
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {
                    "3420822079": {"trainingStatus": 7, "trainingStatusFeedbackPhrase": "PRODUCTIVE_3"}
                }
            }
        }


def test_enrich_populates_all_recovery_fields():
    day = {"calendarDate": "2026-06-18", "restingHeartRate": 64}
    enrich_metric(FakeClient(), "2026-06-18", day)
    assert day["sleepScore"] == 73
    assert day["sleepDurationSeconds"] == 22620
    assert day["hrvOvernight"] == 43.0
    assert day["trainingReadiness"] == 40
    assert day["trainingStatus"] == "PRODUCTIVE_3"


def test_enrich_isolates_a_failing_endpoint():
    # Sleep endpoint blows up; readiness + status must still land.
    day = {"calendarDate": "2026-06-18"}
    enrich_metric(FakeClient(raise_on={"get_sleep_data"}), "2026-06-18", day)
    assert "sleepScore" not in day  # failed endpoint left no key
    assert day["trainingReadiness"] == 40
    assert day["trainingStatus"] == "PRODUCTIVE_3"


def test_enrich_skips_missing_values_without_writing_nulls():
    # Empty/blank payloads must not write null keys (map_metric stays null-tolerant).
    class Blank(FakeClient):
        def get_sleep_data(self, cdate):
            return {}

        def get_training_readiness(self, cdate):
            return []

        def get_training_status(self, cdate):
            return {}

    day = {"calendarDate": "2026-06-18"}
    enrich_metric(Blank(), "2026-06-18", day)
    assert day == {"calendarDate": "2026-06-18"}  # untouched
