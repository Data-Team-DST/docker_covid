"""Tests logging_config — filtre par logger + transmission de extra_data (US-20)."""

import logging

from app.logging_config import (
    TELEMETRY_LOGGER_NAME,
    _AsyncHTTPHandler,
    _LoggerNameFilter,
)


def _make_record(logger_name: str) -> logging.LogRecord:
    """Construit un LogRecord minimal pour tester filtres et handlers."""
    return logging.LogRecord(
        name=logger_name, level=logging.INFO, pathname=__file__,
        lineno=1, msg="msg", args=(), exc_info=None,
    )


class _SyncThread:
    """Remplace threading.Thread en test : exécute la cible immédiatement."""

    def __init__(self, target, args, daemon):  # pylint: disable=unused-argument
        """Capture la cible et ses arguments, comme threading.Thread."""
        self._target = target
        self._args = args

    def start(self) -> None:
        """Exécute la cible de façon synchrone (pas de vrai thread en test)."""
        self._target(*self._args)


def test_logger_name_filter_matches_by_name():
    """_LoggerNameFilter laisse passer uniquement le logger nommé."""
    record = _make_record(TELEMETRY_LOGGER_NAME)
    assert _LoggerNameFilter(TELEMETRY_LOGGER_NAME).filter(record) is True
    assert _LoggerNameFilter("other.logger").filter(record) is False


def test_logger_name_filter_exclude_inverts_match():
    """exclude=True inverse la correspondance de nom."""
    record = _make_record(TELEMETRY_LOGGER_NAME)
    excluded = _LoggerNameFilter(TELEMETRY_LOGGER_NAME, exclude=True)
    other = _LoggerNameFilter("other.logger", exclude=True)
    assert excluded.filter(record) is False
    assert other.filter(record) is True


def test_async_http_handler_includes_extra_data_in_payload(monkeypatch):
    """record.extra_data doit être transmis sous la clé "extra" du payload posté."""
    posted = {}
    monkeypatch.setattr(
        _AsyncHTTPHandler, "_post", lambda self, payload: posted.update(payload)
    )
    monkeypatch.setattr("app.logging_config.threading.Thread", _SyncThread)

    handler = _AsyncHTTPHandler("backend", "http://log-service:5002/v1/log")
    record = _make_record(TELEMETRY_LOGGER_NAME)
    record.extra_data = {"scores": {"COVID": 0.7}}

    handler.emit(record)

    assert posted["extra"] == {"scores": {"COVID": 0.7}}


def test_async_http_handler_omits_extra_when_absent(monkeypatch):
    """Sans extra_data sur le record, le payload ne doit pas contenir "extra"."""
    posted = {}
    monkeypatch.setattr(
        _AsyncHTTPHandler, "_post", lambda self, payload: posted.update(payload)
    )
    monkeypatch.setattr("app.logging_config.threading.Thread", _SyncThread)

    handler = _AsyncHTTPHandler("backend", "http://log-service:5002/v1/log")
    handler.emit(_make_record("app.other"))

    assert "extra" not in posted
