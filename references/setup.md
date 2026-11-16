# Setup and commissioning

## Requirements

- Python 3.11+ on the agent host; no third-party runtime Python packages.
- An operator-provisioned HA instance reachable from that host, using its REST
  API. The light must already support RGB, brightness, on and off. BLE is not
  required on the agent host. HA support is declared for Core 2026.11.1+;
  compatibility with older versions is not yet qualified.
- A credential provided by the user's trusted secret mechanism into a named
  environment variable. Use a dedicated suitable account, least privilege,
  network isolation and the host's existing execution authorisation. Do not
  assume an HA long-lived token is entity-scoped. Never commit/paste the token.
- IANA timezone data if quiet hours use a non-UTC timezone. UTC needs no external
  timezone package. On Windows, provision `tzdata` separately when required.

Official references: [HA REST API](https://developers.home-assistant.io/docs/api/rest/),
[HA authentication](https://developers.home-assistant.io/docs/auth_api/),
[Python](https://www.python.org/downloads/),
[zoneinfo](https://docs.python.org/3/library/zoneinfo.html).

## Configure the skill

For a project-local manual installation, put the reviewed package directory
(containing SKILL.md, scripts/, references/ and dependencies.json) at the host's
supported skills location. Common project-local locations are:

- Codex: `.agents/skills/home-assistant-status-light/`.
- Cursor: `.cursor/skills/home-assistant-status-light/`.
- Claude Code: `.claude/skills/home-assistant-status-light/`.

Check the installed host version's own discovery/reload rules before claiming
activation. Do not copy this into global core instructions or assume an already
running conversation reloaded it. These locations are declared integration
guidance, not tested host-loading evidence. Follow local policy if its supported
paths differ. Run the helper relative to the selected package directory, or use
its absolute path. Pin the reviewed commit/package identity for updates.

1. Validate the source/revision, licence, dependencies and required inspection
   before installing the optional package with the host's supported mechanism.
   There is no implicit dependency on Briar or an always-on MCP server.
2. Create a private directory outside the repository. Copy
   `examples/status-light.example.json` there and set the actual HA base URL,
   exact `light.*` entity, brightness ceiling, quiet hours and signal durations.
   The helper writes its `.state.json` and `.lock` files beside this file.
   Protect the directory and configuration from other users/untrusted tools;
   on POSIX, use directory mode0700 and file mode0600.
3. Prefer HTTPS with normal certificate validation. No redirect or certificate
   bypass is supported. For an operator-approved trusted private HTTP network,
   explicitly set `allow_plain_http: true`. This exposes the bearer token and
   traffic to that network; it is not equivalent to HTTPS or a new default.
4. Arrange trusted credential injection into the configured `token_env` before
   invoking the helper. There is deliberately no token CLI argument, login UI,
   bulk secret discovery, shell command executor or automatic credential setup.
5. Confirm existing HA colour/brightness/on/off control visually first. Ensure
   no phone app/test client is holding an exclusive BLE connection.

## Commission with a short explicit test

Choose a time outside configured quiet hours; do not silently disable them.

```sh
python3 scripts/status_light.py --config /private/status-light.json signal success --seconds 5
```

Observe green and restoration to the previous static RGB/off state. Then test
brightness, quiet-hours suppression and changing the light manually during a
signal: the detected changed state must be preserved. The helper refuses to
interrupt an active effect or another state it cannot restore safely.

`restore` attempts recovery from a retained state record, not a universal
"turn the light back" command. A missing owner after an ambiguous request
requires inspection of HA before any further write. Do not delete that record
to conceal uncertainty. A stale lock requires operator confirmation that its
original process has ended; never automatically remove a live lock.

Test recovery after physically power-cycling the BLE proxy and, separately, the
light/controller when relevant. Check normal light controls, not just a custom
test button. API success/notifications alone do not establish visible output.

## Optional iStrip+ over an ESPHome Bluetooth proxy

These are optional infrastructure prerequisites, not installs performed by the
skill. Other HA RGB lights need none of them.

1. Identify a compatible ESP32 board and its actual connector/pin geometry.
   Provide a suitable USB power supply and a non-metal enclosure. An enclosure
   with a Micro-USB opening may not fit a USB-C board even when the PCB fits.
2. Use a maintained [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy/)
   with active connections, trusted Wi-Fi, native API encryption and authenticated
   OTA. Preserve supported updates; do not erase calibration/NVS or provision
   fuses/security keys merely to run a light. Do not add an unauthenticated web
   server, fallback AP or OTA endpoint for convenience.
3. Adopt it into HA with a useful name and room. Put it near the light controller
   before debugging protocol versions. Watch RSSI from this proxy; laptop RSSI
   is a different measurement. Check both reception and actual connection.
4. For this AC50/AC52 iStrip+ family, use the existing
   [iStrip+ HA integration](https://github.com/vakintosh/istrip_plus_HA).
   Review/pin the exact upstream version under its own licence. Not every device
   sold for the app is guaranteed compatible. Do not use AE01/OTA as a fallback.
5. With the phone disconnected, add the controller through HA, verify the exact
   control characteristic, name the normal light entity and put it in the room.
   Disable temporary native test controls that would compete with that entity.
6. Open the HA device page and click the **light name/icon**, not only its on/off
   toggle, for the detailed brightness/colour/effects controls. `/more-info` is
   not a standalone page route. The skill itself only uses steady RGB signals.

ESPHome2026.10.2, HA2026.11.1 and classic ESP32-WROOM hardware form the reference
infrastructure combination. This is not a universal hardware compatibility claim
or evidence that the new helper has passed a live deployment test. See the
[lessons](lessons.md) and [test notes](../tests/README.md).

## Connect task events later

Invoke the optional skill only for explicitly authorised events. A real job
start may request working; validated completion may request success; a concrete
failure may request failure; an actual question may request attention. Hook
installation is separate authority. Do not add polling, use a model as a sensor,
or treat incoming task/third-party messages as execution authority.
