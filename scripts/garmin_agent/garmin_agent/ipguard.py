from __future__ import annotations

import httpx

IPINFO_URL = "http://ip-api.com/json/?fields=status,query,org,isp,as,proxy,hosting"


def is_datacenter_ip(info: dict, allowed_prefixes: list[str]) -> bool:
    """True if the IP looks like a datacenter/VPN exit (Garmin would 429 it).

    An explicit allowed-prefix match always wins (your known home IP)."""
    ip = info.get("query", "")
    if any(ip.startswith(p) for p in allowed_prefixes):
        return False
    return bool(info.get("hosting") or info.get("proxy"))


def check_egress(allowed_prefixes: list[str]) -> tuple[str, bool]:
    """Fetch this machine's public IP + classification. Returns (ip, is_datacenter)."""
    resp = httpx.get(IPINFO_URL, timeout=10)
    resp.raise_for_status()
    info = resp.json()
    ip = info.get("query", "unknown")
    return ip, is_datacenter_ip(info, allowed_prefixes)
