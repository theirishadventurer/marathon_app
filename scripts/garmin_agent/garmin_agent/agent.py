from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable
from getpass import getpass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from garmin_agent import config as cfgmod
from garmin_agent.api_client import build_payload, poll_requested, post_ingest
from garmin_agent.garmin_fetch import client_from_token, fetch, login_interactive
from garmin_agent.ipguard import check_egress

LOG_PATH = Path(__file__).resolve().parent.parent / "agent.log"
logger = logging.getLogger("garmin_agent")


def _setup_logging() -> None:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)


def run_sync(cfg: cfgmod.AgentConfig) -> bool:
    ip, is_dc = check_egress(cfg.allowed_ip_prefixes)
    if is_dc:
        logger.error(
            "ABORT: egress IP %s looks like a datacenter/VPN exit. Split-tunnel this "
            "python.exe off NordVPN before Garmin will accept it.", ip
        )
        return False
    logger.info("egress IP %s OK (residential)", ip)
    token_blob = cfgmod.get_garth_token()
    if token_blob is None:
        logger.error("No cached Garmin token — run `--login` once interactively.")
        return False
    client = client_from_token(token_blob)
    activities, metrics = fetch(client, cfg.lookback_days)
    result = post_ingest(cfg, cfgmod.get_ingest_token(), build_payload(activities, metrics))
    logger.info(
        "ingest ok: +%s activities, +%s metrics, %s skipped",
        result["synced_activities"], result["synced_metrics"], result["skipped"],
    )
    return True


def watch(cfg: cfgmod.AgentConfig) -> None:
    logger.info("watch mode: startup catch-up sync")
    _safe(run_sync, cfg)
    last_periodic = time.monotonic()
    try:
        token = cfgmod.get_ingest_token()
    except Exception:  # noqa: BLE001
        logger.error(
            "Cannot read ingest token; on-demand polling disabled. Run --set-secrets, then restart."
        )
        token = None
    while True:
        time.sleep(cfg.poll_seconds)
        if token is not None:
            try:
                if poll_requested(cfg, token):
                    logger.info("on-demand sync requested")
                    _safe(run_sync, cfg)
            except Exception as exc:  # noqa: BLE001
                logger.warning("poll failed: %s", exc)
        if time.monotonic() - last_periodic >= cfg.periodic_hours * 3600:
            logger.info("periodic sync")
            _safe(run_sync, cfg)
            last_periodic = time.monotonic()


def _safe(fn: Callable[[cfgmod.AgentConfig], bool], cfg: cfgmod.AgentConfig) -> None:
    try:
        fn(cfg)
    except Exception:  # noqa: BLE001
        logger.exception("sync run failed")


def main() -> None:
    _setup_logging()
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true", help="single sync then exit")
    g.add_argument("--watch", action="store_true", help="poll loop + periodic sync")
    g.add_argument("--login", action="store_true", help="interactive Garmin login (mints token)")
    g.add_argument("--set-secrets", action="store_true", help="store ingest token in keyring")
    args = ap.parse_args()
    cfg = cfgmod.load_config()

    if args.login:
        cfgmod.set_garth_token(login_interactive(cfg.garmin_email))
        logger.info("Garmin token cached. You can now run --once / --watch.")
    elif args.set_secrets:
        cfgmod.set_ingest_token(getpass("Ingest token: "))
        logger.info("Ingest token stored in Windows Credential Manager.")
    elif args.once:
        try:
            if not run_sync(cfg):
                sys.exit(1)
        except Exception:  # noqa: BLE001
            logger.exception("sync failed")
            sys.exit(1)
    elif args.watch:
        watch(cfg)
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
