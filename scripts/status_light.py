"""One-light HA status signals. SPDX-License-Identifier: GPL-3.0-or-later.

Assisted-by: Briar. Runtime dependencies: Python standard library only.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib import error, parse, request
from zoneinfo import ZoneInfo

COLOURS = {"working": [0, 0, 255], "success": [0, 255, 0],
           "attention": [255, 120, 0], "failure": [255, 0, 0]}


class Failure(Exception):
    """Safe diagnostic: never includes a token, URL or HTTP response body."""


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def rgb(value):
    return isinstance(value, list) and len(value) == 3 and all(integer(v, 0, 255) for v in value)


def config(path):
    try:
        value = json.loads(Path(path).read_text())
        url = parse.urlsplit(value["base_url"])
        if (url.scheme not in ("http", "https") or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError()
        if url.scheme == "http" and value.get("allow_plain_http") is not True:
            raise Failure("Plain HTTP requires explicit trusted-network configuration")
        if not re.fullmatch(r"light\.[a-z0-9_]+", value["entity_id"]):
            raise ValueError()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value["token_env"]):
            raise ValueError()
        ceiling = value.get("max_brightness_pct", 20)
        if not integer(ceiling, 1, 100):
            raise ValueError()
        signals = value.setdefault("signals", {})
        if set(signals) - set(COLOURS):
            raise ValueError()
        for name, default in COLOURS.items():
            signal = signals.setdefault(name, {})
            signal.setdefault("rgb", default)
            signal.setdefault("brightness_pct", min(20, ceiling))
            signal.setdefault("seconds", 10 if name in ("success", "failure") else 30)
            if not rgb(signal["rgb"]) or not integer(signal["brightness_pct"], 1, ceiling):
                raise ValueError()
            seconds(signal["seconds"])
        if value.get("quiet_hours"):
            quiet(value, datetime.now(timezone.utc))  # Validate zone and clock format.
        return value
    except Failure:
        raise
    except Exception:
        raise Failure("Invalid configuration") from None


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise Failure("Duration must be a positive finite number")
    return value


def quiet(cfg, now):
    hours = cfg.get("quiet_hours")
    if not hours:
        return False
    zone = timezone.utc if hours["timezone"] == "UTC" else ZoneInfo(hours["timezone"])
    def minutes(text):
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
            raise ValueError()
        h, m = map(int, text.split(":"))
        return h * 60 + m
    start, end = minutes(hours["start"]), minutes(hours["end"])
    if start == end:
        raise ValueError()
    local = now.astimezone(zone)
    current = local.hour * 60 + local.minute
    return start <= current < end if start < end else current >= start or current < end


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Failure("HTTP redirects are not permitted")


class HA:
    def __init__(self, cfg):
        self.cfg = cfg
        self.token = os.environ.get(cfg["token_env"])
        if not self.token or "\n" in self.token or "\r" in self.token:
            raise Failure("Configured credential environment is unavailable")
        self.opener = request.build_opener(NoRedirect())

    def call(self, path, body=None):
        payload = None if body is None else json.dumps(body).encode()
        req = request.Request(self.cfg["base_url"].rstrip("/") + path,
            data=payload, headers={"Authorization": "Bearer " + self.token,
                                    "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=15) as response:
                return json.load(response)
        except Failure:
            raise
        except (error.URLError, OSError, ValueError):
            raise Failure("HA request failed; a write may have occurred") from None

    def state(self):
        state = self.call("/api/states/" + self.cfg["entity_id"])
        if state.get("entity_id") != self.cfg["entity_id"]:
            raise Failure("HA returned the wrong entity")
        return state

    def set(self, state):
        # Construct a fixed allowlisted service body; never forward arbitrary attributes.
        if state.get("state") not in ("on", "off"):
            raise Failure("Only light on/off services are supported")
        body = {"entity_id": self.cfg["entity_id"]}
        if state["state"] == "on":
            if not rgb(state.get("rgb")) or not integer(state.get("brightness"), 1, 255):
                raise Failure("Invalid static RGB command")
            body.update(rgb_color=state["rgb"], brightness=state["brightness"])
        return self.call("/api/services/light/turn_" + state["state"], body)


def snapshot(state):
    if state.get("state") not in ("on", "off"):
        raise Failure("Light is unavailable or unsupported")
    if state["state"] == "off":
        return {"state": "off"}
    attrs = state.get("attributes", {})
    if attrs.get("effect") or not rgb(attrs.get("rgb_color")) or not integer(attrs.get("brightness"), 1, 255):
        raise Failure("Previous light state cannot be safely restored as static RGB")
    return {"state": "on", "rgb": attrs["rgb_color"], "brightness": attrs["brightness"]}


def fingerprint(state):
    context = state.get("context", {}).get("id")
    if not isinstance(context, str) or not context or not state.get("last_updated"):
        raise Failure("HA ownership context is missing")
    return hashlib.sha256(json.dumps({"context": context, "updated": state["last_updated"],
        "display": snapshot(state)}, sort_keys=True).encode()).hexdigest()


def same_display(actual, wanted):
    got = snapshot(actual)
    return got == wanted or (got["state"] == wanted["state"] == "on"
        and got["rgb"] == wanted["rgb"] and abs(got["brightness"] - wanted["brightness"]) <= 1)


class Controller:
    def __init__(self, cfg, path, ha, sleep=time.sleep):
        self.cfg, self.ha, self.sleep = cfg, ha, sleep
        self.record = Path(str(path) + ".state.json")
        self.lock = Path(str(path) + ".lock")

    @contextmanager
    def exclusive(self):
        try:
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise Failure("Another operation or stale lock exists; inspect before recovery") from None
        try:
            with os.fdopen(fd, "w") as output:
                output.write(str(os.getpid()))
            yield
        finally:
            self.lock.unlink()

    def save(self, value):
        fd, name = tempfile.mkstemp(prefix=".status-light-", dir=self.record.parent)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump(value, output)
            os.replace(name, self.record)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def restore(self):
        if not self.record.exists():
            return {"restored": False, "reason": "no_snapshot"}
        try:
            record = json.loads(self.record.read_text())
            if record["entity"] != self.cfg["entity_id"] or record["base_url"] != self.cfg["base_url"]:
                raise Failure("Snapshot target differs from configuration")
            before = record["before"]
            if before not in ({"state": "off"},):
                snapshot({"state": before["state"], "attributes": {
                    "rgb_color": before["rgb"], "brightness": before["brightness"]}})
            if not record["owner"]:
                raise Failure("Previous write is ambiguous; inspect HA before restoring")
        except Failure:
            raise
        except Exception:
            raise Failure("Invalid recovery record") from None
        if fingerprint(self.ha.state()) != record["owner"]:
            self.record.unlink()
            return {"restored": False, "reason": "light_changed_preserved"}
        self.ha.set(before)
        if not same_display(self.ha.state(), before):
            raise Failure("Restoration was not verified; recovery record retained")
        self.record.unlink()
        return {"restored": True}

    def signal(self, name, duration=None, now=None):
        if quiet(self.cfg, now or datetime.now(timezone.utc)):
            return {"signalled": False, "reason": "quiet_hours"}
        if self.record.exists():
            raise Failure("Recovery record exists; restore or inspect before a new signal")
        signal = self.cfg["signals"][name]
        duration = seconds(signal["seconds"] if duration is None else duration)
        wanted = {"state": "on", "rgb": signal["rgb"],
                  "brightness": round(signal["brightness_pct"] * 255 / 100)}
        before = snapshot(self.ha.state())
        record = {"entity": self.cfg["entity_id"], "base_url": self.cfg["base_url"],
                  "before": before, "owner": None}
        self.save(record)
        self.ha.set(wanted)
        current = self.ha.state()
        if not same_display(current, wanted):
            raise Failure("Signal state was not verified; recovery record retained")
        record["owner"] = fingerprint(current)
        self.save(record)
        print(json.dumps({"event": "signal_active", "status": name, "seconds": duration}), flush=True)
        try:
            self.sleep(duration)
        finally:
            result = self.restore()
        return {"signalled": True, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    commands = parser.add_subparsers(dest="action", required=True)
    signal = commands.add_parser("signal")
    signal.add_argument("status", choices=tuple(COLOURS))
    signal.add_argument("--seconds", type=float)
    commands.add_parser("restore")
    args = parser.parse_args()
    try:
        cfg = config(args.config)
        controller = Controller(cfg, args.config, HA(cfg))
        with controller.exclusive():
            result = controller.signal(args.status, args.seconds) if args.action == "signal" else controller.restore()
        print(json.dumps({"ok": True, **result}))
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "Interrupted; check restoration result"}))
        raise SystemExit(130)
    except Failure as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise SystemExit(1)
    except Exception:
        print(json.dumps({"ok": False, "error": "Local operation failed; inspect private state"}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
