from app.models.workout import WorkoutFamily, WorkoutType

_PLANNED_TO_FAMILY: dict[WorkoutType, WorkoutFamily] = {
    WorkoutType.easy: WorkoutFamily.running,
    WorkoutType.long: WorkoutFamily.running,
    WorkoutType.tempo: WorkoutFamily.running,
    WorkoutType.intervals: WorkoutFamily.running,
    WorkoutType.hills: WorkoutFamily.running,
    WorkoutType.mp_long: WorkoutFamily.running,
    WorkoutType.recovery: WorkoutFamily.running,
    WorkoutType.strides: WorkoutFamily.running,
    WorkoutType.race: WorkoutFamily.running,
    WorkoutType.strength_a: WorkoutFamily.strength,
    WorkoutType.strength_b: WorkoutFamily.strength,
    WorkoutType.cross: WorkoutFamily.other,
    WorkoutType.rest: WorkoutFamily.other,
}

_GARMIN_RUNNING_TYPES = {
    "running",
    "trail_running",
    "treadmill_running",
    "track_running",
    "indoor_running",
    "virtual_run",
}

_GARMIN_STRENGTH_TYPES = {"strength_training"}


def family_for_planned(workout_type: WorkoutType) -> WorkoutFamily:
    return _PLANNED_TO_FAMILY[workout_type]


def family_for_garmin_activity_type(activity_type: str) -> WorkoutFamily:
    normalized = activity_type.lower().strip()
    if normalized in _GARMIN_RUNNING_TYPES:
        return WorkoutFamily.running
    if normalized in _GARMIN_STRENGTH_TYPES:
        return WorkoutFamily.strength
    return WorkoutFamily.other


_STRAVA_RUNNING_TYPES = {
    "run",
    "trailrun",
    "virtualrun",
    "treadmill",
}

_STRAVA_STRENGTH_TYPES = {"weighttraining", "workout", "crossfit"}


def family_for_strava_sport_type(sport_type: str) -> WorkoutFamily:
    normalized = sport_type.lower().strip()
    if normalized in _STRAVA_RUNNING_TYPES:
        return WorkoutFamily.running
    if normalized in _STRAVA_STRENGTH_TYPES:
        return WorkoutFamily.strength
    return WorkoutFamily.other
