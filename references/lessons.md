# BLE light lessons

These are reusable engineering cautions, not private deployment records or
instructions to repeat past firmware experiments.

- **Place the proxy first.** A laptop/phone connecting successfully does not
  prove a small ESP32 has the same link budget. Compare RSSI from the actual
  proxy before/after moving it. Negative dBm nearer zero is stronger, but no
  universal RSSI cutoff proves reliable connections. Advertisement RSSI measures
  one reception direction, not how well the controller hears the proxy.
- **Advertisements are not connections.** Discovery can work while link
  establishment fails. Error0x3e means connection establishment failed; it is
  not proof of a bad RGB payload. Separate scan, link, discovery, subscribe,
  join, write and visible-output results.
- **One success is capability, not reliability.** Preserve a known-good image
  and its identity. Compare fresh connections, a sustained session and physical
  power-cycle recovery. Do not keep replaying an unchanged failure.
- **Match the protocol family.** For the AC50/AC52 family documented by the
  [upstream integration](https://github.com/vakintosh/istrip_plus_HA/blob/main/docs/ble-protocol.md),
  AF30 advertising does not identify the control service. AC50 is the service;
  AC52 is the control write characteristic. AE00/AE01 are firmware-update
  interfaces, not an arbitrary writable fallback.
- **A connected controller may still ignore commands.** This family uses a
  join-group message before RGB per connection. The documented app subscribes
  to notifications. A separate power-on opcode is not established: ordinary
  on/off can be RGB with nonzero/zero brightness. Do not guess undocumented
  commands. Notification counts alone are not per-command acknowledgments.
- **Isolate layers.** A simple ESP32 client exchanging numbered data with a
  known-good reference peripheral tests its basic central/GATT path. That does
  not prove interoperability or identical RF conditions with the strip.
- **Use a single control owner.** A phone app, native BLE test client and HA
  integration can compete. Release temporary clients and disable test buttons
  when the normal HA light owns the connection. Do not start a second BLE
  advertisement consumer alongside HA merely to obtain another log.
- **Test the delivered path.** A custom alternating button is not the same as
  the normal HA light entity. Verify colour, brightness and off/on through the
  normal entity, then physically power-cycle the proxy and repeat.
- **Keep security and recovery intact.** Encryption, authenticated OTA, scoped
  credentials and supported recovery are not expendable debugging options.
  Do not leave development drivers/services permanently enabled without need.
- **Only promise the addressing that was proved.** Whole-strip RGB and built-in
  effects do not imply individual LED addressing or a segmented progress bar.

Upstream protocol statements have their own evidence/compatibility limits.
Do not treat this document, an example configuration or a saved receipt as
permission to flash, install, pair, operate another device or run effects.
