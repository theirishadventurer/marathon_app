from app.lib.workout_family import family_for_strava_sport_type
from app.models.workout import WorkoutFamily


def test_strava_run_types_map_to_running():
    for t in ["Run", "TrailRun", "VirtualRun", "Treadmill"]:
        assert family_for_strava_sport_type(t) == WorkoutFamily.running


def test_strava_strength_maps_to_strength():
    assert family_for_strava_sport_type("WeightTraining") == WorkoutFamily.strength
    assert family_for_strava_sport_type("Workout") == WorkoutFamily.strength


def test_strava_unknown_maps_to_other():
    assert family_for_strava_sport_type("Ride") == WorkoutFamily.other
    assert family_for_strava_sport_type("") == WorkoutFamily.other
