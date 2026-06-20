import types

import pytest

from garmin_agent import ipguard
from garmin_agent.ipguard import check_egress, is_datacenter_ip


# ---------------------------------------------------------------------------
# Original 4 tests (must stay green)
# ---------------------------------------------------------------------------


def test_hosting_flag_is_datacenter():
    info = {"query": "203.0.113.5", "hosting": True, "proxy": False}
    assert is_datacenter_ip(info, []) is True


def test_proxy_flag_is_datacenter():
    # proxy IS present (no hosting key) — missing-fields branch must NOT trigger
    assert is_datacenter_ip({"query": "203.0.113.5", "proxy": True}, []) is True


def test_residential_is_not_datacenter():
    info = {"query": "98.42.10.7", "hosting": False, "proxy": False}
    assert is_datacenter_ip(info, []) is False


def test_allowed_prefix_overrides():
    info = {"query": "98.42.10.7", "hosting": True}  # flagged but whitelisted
    assert is_datacenter_ip(info, ["98.42."]) is False


# ---------------------------------------------------------------------------
# New fail-closed tests
# ---------------------------------------------------------------------------


def test_missing_classification_fields_is_datacenter():
    """No hosting/proxy keys at all → fail closed → datacenter."""
    assert is_datacenter_ip({"query": "1.2.3.4"}, []) is True


def test_allowed_prefix_wins_even_when_unclassifiable():
    """Whitelisted prefix beats the missing-fields fail-closed branch."""
    assert is_datacenter_ip({"query": "98.42.1.1"}, ["98.42."]) is False


def test_check_egress_raises_on_api_failure(monkeypatch):
    """check_egress must raise RuntimeError when ip-api returns status!=success."""

    class FakeResp:
        def raise_for_status(self):
            pass  # HTTP 200 — raise_for_status is a no-op

        def json(self):
            return {"status": "fail", "message": "reserved range", "query": "10.0.0.1"}

    monkeypatch.setattr(ipguard.httpx, "get", lambda *a, **kw: FakeResp())

    with pytest.raises(RuntimeError, match="reserved range"):
        check_egress([])


def test_check_egress_happy_path(monkeypatch):
    """check_egress returns (ip, False) for a clean residential IP."""

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "success",
                "query": "98.42.10.7",
                "hosting": False,
                "proxy": False,
            }

    monkeypatch.setattr(ipguard.httpx, "get", lambda *a, **kw: FakeResp())

    result = check_egress([])
    assert result == ("98.42.10.7", False)
