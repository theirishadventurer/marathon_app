from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(athlete_id: str) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_expiry_days)
    payload = {"sub": athlete_id, "exp": expires_at}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_at


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


def create_strava_state_token(athlete_id: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    payload = {"sub": athlete_id, "purpose": "strava_oauth", "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_strava_state_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None
    if payload.get("purpose") != "strava_oauth":
        return None
    return payload.get("sub")
