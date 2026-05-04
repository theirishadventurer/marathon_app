from app.lib.workout_family import family_for_garmin_activity_type, family_for_planned
from app.models.workout import WorkoutFamily, WorkoutType


def test_all_workout_types_map_to_family():
    for wt in WorkoutType:
        result = family_for_planned(wt)
        assert isinstance(result, WorkoutFamily), f"{wt} did not return a WorkoutFamily"


def test_running_family():
    running_types = [
        WorkoutType.easy, WorkoutType.long, WorkoutType.tempo,
        WorkoutType.intervals, WorkoutType.hills, WorkoutType.mp_long,
        WorkoutType.recovery, WorkoutType.strides, WorkoutType.race,
    ]
    for wt in running_types:
        assert family_for_planned(wt) == WorkoutFamily.running


def test_strength_family():
    assert family_for_planned(WorkoutType.strength_a) == WorkoutFamily.strength
    assert family_for_planned(WorkoutType.strength_b) == WorkoutFamily.strength


def test_other_family():
    assert family_for_planned(WorkoutType.cross) == WorkoutFamily.other
    assert family_for_planned(WorkoutType.rest) == WorkoutFamily.other


def test_garmin_running():
    assert family_for_garmin_activity_type("running") == WorkoutFamily.running
    assert family_for_garmin_activity_type("trail_running") == WorkoutFamily.running
    assert family_for_garmin_activity_type("treadmill_running") == WorkoutFamily.running


def test_garmin_strength():
    assert family_for_garmin_activity_type("strength_training") == WorkoutFamily.strength


def test_garmin_other():
    assert family_for_garmin_activity_type("cycling") == WorkoutFamily.other
    assert family_for_garmin_activity_type("swimming") == WorkoutFamily.other
    assert family_for_garmin_activity_type("unknown_activity") == WorkoutFamily.other
