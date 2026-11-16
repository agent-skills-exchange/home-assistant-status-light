# Home Assistant status light

An optional [Agent Skills](https://agentskills.io/specification) package for
showing task status on one Home Assistant RGB light. It works independently of
Briar and does not require an agent-host Bluetooth adapter or a particular
editor. Original work is GPL-3.0-or-later. Assisted-by: Briar.

## What it provides

- Configurable steady signals: working, success, attention and failure.
- A brightness ceiling and optional quiet hours.
- Foreground timed restoration with a private recovery record.
- Context/state checks that preserve a detected manual override.
- An explicit dependency manifest and optional iStrip+/ESPHome setup guidance.

No automatic task hooks, polling, strobe effects, firmware installer or secret
resolver is included. Installation/loading does not grant control authority.

Start with [setup and commissioning](references/setup.md), then read the narrow
[SKILL.md](SKILL.md) instructions when the capability is needed. Useful
[BLE/HA lessons](references/lessons.md) are separate, not always-loaded policy.
Dependencies are declared in [dependencies.json](dependencies.json).
Format and interoperability checks are documented in
[Agent Skills compatibility](references/compatibility.md). The dependency
manifest is an optional Exchange extension, not an Agent Skills core field or
an automatic installer.

CI checks the official Python Agent Skills reference format, the bundled draft
dependency schema and local file references, alongside runtime regression tests.
For the proposed HA-side expiry approach and commissioning gates, see
[durable restoration](references/durable-restoration.md). This design is not
implemented or installed; the current helper still restores in the foreground.

```sh
python3 scripts/status_light.py --config /private/status-light.json signal working
python3 scripts/status_light.py --config /private/status-light.json signal success --seconds 10
python3 scripts/status_light.py --config /private/status-light.json restore
python3 -m unittest discover -s tests -v
```

The configured credential must already be supplied through trusted process
plumbing. Never paste it into a command or skill prompt. An HA token can have
more permissions than the helper uses; a client allowlist is not a scoped token.

## Limits and support claims

The helper uses only the Python standard library. Python 3.11+ is required;
platform declarations and actual test evidence are kept distinct in the
manifest and [test notes](tests/README.md). Core format compliance is not proof
that a host has loaded the skill or that its HA integration is configured.

Timed expiry is best effort while the foreground process remains alive. Power
loss, SIGKILL, network loss or HA failure can leave the last colour displayed.
Manual-override detection checks the HA context/state immediately before
restoring; it is not an atomic compare-and-set and has a small race window.
Unchanged-value manual actions may not create distinguishable HA state. Use one
private configuration per light. Do not claim cross-configuration locking or
server-side leases. A durable unattended deployment needs separately authorised
HA-side lifetime/ownership controls and acceptance testing.

The initial implementation was merged in PR #1 after passing hosted CI and
static checks, under a maintainer-approved exact-revision exception to pending
independent review. That exception does not cover later changes. Merge is not
independent review, live commissioning or activation. The package does not
install itself or activate any host/global instructions.
