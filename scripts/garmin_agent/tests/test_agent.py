"""Tests for agent.py entry-point safety guards."""
from __future__ import annotations

import pytest

from garmin_agent import agent
from garmin_agent.config import AgentConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_cfg() -> AgentConfig:
    """Build a minimal AgentConfig without touching env vars or keyring."""
    return AgentConfig(
        api_url="http://localhost:8000",
        garmin_email="test@example.com",
        lookback_days=1,
        poll_seconds=60,
        periodic_hours=6,
        allowed_ip_prefixes=[],
    )


# ---------------------------------------------------------------------------
# Test 1: datacenter IP short-circuits run_sync (returns False, no network)
# ---------------------------------------------------------------------------


def test_run_sync_aborts_on_datacenter_ip(monkeypatch):
    """When check_egress flags the IP as datacenter, run_sync must return False
    without ever calling fetch or post_ingest."""

    fetch_called = []
    post_ingest_called = []

    monkeypatch.setattr(agent, "check_egress", lambda _prefixes: ("203.0.113.5", True))
    monkeypatch.setattr(agent.cfgmod, "get_garth_token", lambda: "fake-token-blob")
    monkeypatch.setattr(agent, "client_from_token", lambda _blob: object())
    monkeypatch.setattr(agent, "fetch", lambda _client, _days: fetch_called.append(1) or ([], []))
    monkeypatch.setattr(agent, "post_ingest", lambda *_a, **_kw: post_ingest_called.append(1))

    result = agent.run_sync(_minimal_cfg())

    assert result is False, "run_sync must return False when datacenter IP is detected"
    assert not fetch_called, "fetch must NOT be called when the IP guard aborts"
    assert not post_ingest_called, "post_ingest must NOT be called when the IP guard aborts"


# ---------------------------------------------------------------------------
# Test 2: RuntimeError from check_egress propagates out of run_sync
# ---------------------------------------------------------------------------


def test_run_sync_propagates_check_egress_error(monkeypatch):
    """When check_egress raises RuntimeError (e.g. ip-api lookup failure),
    run_sync must let it propagate so --once's try/except can catch it."""

    monkeypatch.setattr(
        agent, "check_egress", lambda _prefixes: (_ for _ in ()).throw(RuntimeError("ip-api lookup failed"))
    )

    with pytest.raises(RuntimeError, match="ip-api lookup failed"):
        agent.run_sync(_minimal_cfg())
