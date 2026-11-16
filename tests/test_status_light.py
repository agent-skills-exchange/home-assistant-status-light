import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("status_light", ROOT / "scripts/status_light.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def state(colour=(100, 100, 100), brightness=80, context="initial", status="on"):
    return {"entity_id": "light.status_strip", "state": status,
            "context": {"id": context}, "last_updated": context,
            "attributes": {"rgb_color": list(colour), "brightness": brightness}}


class FakeHA:
    def __init__(self):
        self.current = state()
        self.calls = []
        self.fail_write = False

    def state(self):
        return copy.deepcopy(self.current)

    def set(self, value):
        self.calls.append(copy.deepcopy(value))
        if self.fail_write:
            raise app.Failure("Synthetic ambiguous write")
        self.current = state(value.get("rgb", (0, 0, 0)), value.get("brightness", 1),
                             "write-" + str(len(self.calls)), value["state"])


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        self.data = json.loads((ROOT / "examples/status-light.example.json").read_text())
        self.data.pop("quiet_hours")
        self.write()
        self.cfg = app.config(self.path)
        self.ha = FakeHA()
        self.controller = app.Controller(self.cfg, self.path, self.ha, sleep=lambda _: None)

    def write(self):
        self.path.write_text(json.dumps(self.data))

    def test_defaults(self):
        self.assertEqual(set(self.cfg["signals"]), set(app.COLOURS))
        self.assertTrue(all(x["brightness_pct"] <= 20 for x in self.cfg["signals"].values()))

    def test_invalid_target(self):
        for target in ("switch.other", "light.x/api/services", "light.x\n", "light.*"):
            with self.subTest(target=target):
                self.data["entity_id"] = target
                self.write()
                with self.assertRaises(app.Failure): app.config(self.path)

    def test_bad_urls(self):
        for url in ("file:///synthetic/non-network-input", "https://user:pass@invalid", "https://invalid?q=x", "https://invalid#x", "http://invalid"):
            with self.subTest(url=url):
                self.data["base_url"] = url
                self.write()
                with self.assertRaises(app.Failure): app.config(self.path)

    def test_http_is_explicit(self):
        self.data.update(base_url="http://ha.example.invalid", allow_plain_http=True)
        self.write()
        self.assertTrue(app.config(self.path)["allow_plain_http"])

    def test_brightness_and_rgb_validation(self):
        for change in ({"brightness_pct": 21}, {"brightness_pct": True}, {"rgb": [0, 0, 256]}, {"rgb": [False, 0, 0]}):
            with self.subTest(change=change):
                self.data["signals"]["working"].update(change)
                self.write()
                with self.assertRaises(app.Failure): app.config(self.path)

    def test_duration_validation(self):
        for value in (0, -1, float("nan"), float("inf"), True, "10"):
            with self.subTest(value=value):
                with self.assertRaises(app.Failure): app.seconds(value)

    def test_quiet_hours_overnight(self):
        cfg = {"quiet_hours": {"timezone": "UTC", "start": "22:00", "end": "08:00"}}
        for hour, expected in ((22, True), (23, True), (0, True), (7, True), (8, False), (21, False)):
            self.assertEqual(app.quiet(cfg, datetime(2026, 1, 1, hour, tzinfo=timezone.utc)), expected)

    def test_quiet_hours_suppress_without_calls(self):
        self.cfg["quiet_hours"] = {"timezone": "UTC", "start": "22:00", "end": "08:00"}
        result = self.controller.signal("working", now=datetime(2026, 1, 1, 23, tzinfo=timezone.utc))
        self.assertEqual(result["reason"], "quiet_hours")
        self.assertEqual(self.ha.calls, [])
        self.assertFalse(self.controller.record.exists())

    def test_signal_and_restore(self):
        before = app.snapshot(self.ha.state())
        result = self.controller.signal("working", 1)
        self.assertTrue(result["restored"])
        self.assertEqual(app.snapshot(self.ha.state()), before)
        self.assertEqual(self.ha.calls[0], {"state": "on", "rgb": [0, 0, 255], "brightness": 51})
        self.assertFalse(self.controller.record.exists())

    def test_restore_off(self):
        self.ha.current = state(status="off")
        self.controller.signal("success", 1)
        self.assertEqual(self.ha.calls[-1], {"state": "off"})

    def test_manual_override_preserved(self):
        def override(_): self.ha.current = state((255, 255, 255), 200, "manual")
        self.controller.sleep = override
        result = self.controller.signal("failure", 1)
        self.assertEqual(result["reason"], "light_changed_preserved")
        self.assertEqual(len(self.ha.calls), 1)

    def test_same_colour_manual_context_preserved(self):
        def override(_): self.ha.current["context"] = {"id": "manual-same-colour"}
        self.controller.sleep = override
        result = self.controller.signal("attention", 1)
        self.assertFalse(result["restored"])

    def test_interrupt_restores(self):
        def interrupt(_): raise KeyboardInterrupt()
        self.controller.sleep = interrupt
        with self.assertRaises(KeyboardInterrupt): self.controller.signal("working", 1)
        self.assertEqual(len(self.ha.calls), 2)
        self.assertFalse(self.controller.record.exists())

    def test_ambiguous_write_retains_record(self):
        self.ha.fail_write = True
        with self.assertRaises(app.Failure): self.controller.signal("working", 1)
        self.assertTrue(self.controller.record.exists())
        self.ha.fail_write = False
        with self.assertRaises(app.Failure): self.controller.restore()
        self.assertEqual(len(self.ha.calls), 1)

    def test_previous_effect_refused(self):
        self.ha.current["attributes"]["effect"] = "unqualified-effect"
        with self.assertRaises(app.Failure): self.controller.signal("success", 1)
        self.assertEqual(self.ha.calls, [])

    def test_unavailable_refused(self):
        self.ha.current["state"] = "unavailable"
        with self.assertRaises(app.Failure): self.controller.signal("success", 1)
        self.assertEqual(self.ha.calls, [])

    def test_missing_context_retains_recovery(self):
        self.ha.current.pop("context")
        with self.assertRaises(app.Failure): app.fingerprint(self.ha.state())

    def test_exclusive_lock(self):
        with self.controller.exclusive():
            with self.assertRaises(app.Failure):
                with self.controller.exclusive(): pass
        self.assertFalse(self.controller.lock.exists())

    def test_existing_record_blocks_new_signal(self):
        self.controller.save({})
        with self.assertRaises(app.Failure): self.controller.signal("working", 1)
        self.assertEqual(self.ha.calls, [])

    def test_snapshot_target_mismatch(self):
        self.controller.save({"entity": "light.other", "base_url": self.cfg["base_url"]})
        with self.assertRaises(app.Failure): self.controller.restore()
        self.assertEqual(self.ha.calls, [])

    def test_private_record_mode(self):
        self.controller.save({"dummy": True})
        if os.name == "posix": self.assertEqual(self.controller.record.stat().st_mode & 0o777, 0o600)

    def test_no_redirect(self):
        with self.assertRaises(app.Failure): app.NoRedirect().redirect_request(None, None, 302, None, {}, "https://other.invalid")

    def test_no_credentials_in_diagnostic(self):
        with patch.dict(os.environ, {self.cfg["token_env"]: "synthetic-test-token"}):
            ha = app.HA(self.cfg)
            with patch.object(ha.opener, "open", side_effect=app.error.URLError("synthetic-test-token")):
                with self.assertRaises(app.Failure) as error: ha.state()
                self.assertNotIn("synthetic-test-token", str(error.exception))

    def test_only_fixed_service_and_entity(self):
        with patch.dict(os.environ, {self.cfg["token_env"]: "synthetic-test-token"}):
            ha = app.HA(self.cfg)
            with patch.object(ha, "call") as call:
                ha.set({"state": "on", "rgb": [0, 0, 255], "brightness": 51, "untrusted": "ignored"})
            call.assert_called_once_with("/api/services/light/turn_on", {
                "entity_id": "light.status_strip", "rgb_color": [0, 0, 255], "brightness": 51})

    def test_wrong_entity_return_refused(self):
        with patch.dict(os.environ, {self.cfg["token_env"]: "synthetic-test-token"}):
            ha = app.HA(self.cfg)
            with patch.object(ha, "call", return_value={"entity_id": "light.other"}):
                with self.assertRaises(app.Failure): ha.state()

    def test_invalid_service_state_refused(self):
        with patch.dict(os.environ, {self.cfg["token_env"]: "synthetic-test-token"}):
            ha = app.HA(self.cfg)
            with patch.object(ha, "call") as call:
                with self.assertRaises(app.Failure): ha.set({"state": "other"})
                call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
