from garmin_agent.ipguard import is_datacenter_ip


def test_hosting_flag_is_datacenter():
    info = {"query": "203.0.113.5", "hosting": True, "proxy": False}
    assert is_datacenter_ip(info, []) is True


def test_proxy_flag_is_datacenter():
    assert is_datacenter_ip({"query": "203.0.113.5", "proxy": True}, []) is True


def test_residential_is_not_datacenter():
    info = {"query": "98.42.10.7", "hosting": False, "proxy": False}
    assert is_datacenter_ip(info, []) is False


def test_allowed_prefix_overrides():
    info = {"query": "98.42.10.7", "hosting": True}  # flagged but whitelisted
    assert is_datacenter_ip(info, ["98.42."]) is False
