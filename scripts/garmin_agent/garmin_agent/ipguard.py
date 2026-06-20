from __future__ import annotations

import httpx

# ip-api.com free tier is HTTP-only (no HTTPS available). A MITM could spoof the
# response and bypass this guard, but worst-case is a degraded Garmin sync, not
# asset compromise — accepted limitation.
IPINFO_URL = "http://ip-api.com/json/?fields=status,query,org,isp,as,proxy,hosting"


def is_datacenter_ip(info: dict, allowed_prefixes: list[str]) -> bool:
    """True if the IP looks like a datacenter/VPN exit (Garmin would 429 it).

    Evaluation order (fail-closed):
    1. Allowed-prefix match always wins — a whitelisted home IP returns False even
       when classification fields are missing.
    2. Missing ``hosting``/``proxy`` fields → treat as datacenter (fail closed).
    3. Otherwise return True if either flag is truthy.
    """
    ip = info.get("query", "")
    if any(ip.startswith(p) for p in allowed_prefixes):
        return False
    if "hosting" not in info and "proxy" not in info:
        return True  # cannot classify -> fail closed, treat as datacenter
    return bool(info.get("hosting") or info.get("proxy"))


def check_egress(allowed_prefixes: list[str]) -> tuple[str, bool]:
    """Fetch this machine's public IP + classification. Returns (ip, is_datacenter)."""
    resp = httpx.get(IPINFO_URL, timeout=10)
    resp.raise_for_status()
    info = resp.json()
    if info.get("status") != "success":
        raise RuntimeError(f"ip-api lookup failed: {info.get('message', 'unknown')}")
    ip = info.get("query", "unknown")
    return ip, is_datacenter_ip(info, allowed_prefixes)
