"""One clock for the app, so timers, the demo seed and tests can pass an explicit time."""
import datetime as dt


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def as_utc(value: dt.datetime | None) -> dt.datetime:
    return (value or utcnow()).astimezone(dt.timezone.utc)
