# Durable restoration: design and commissioning gates

Status: proposed design only. No HA package, service endpoint, automatic task
hook or durable mode is implemented by this skill. The current helper retains
best-effort foreground restoration. This document is not installation authority.

## Why a simple HA delay is insufficient

Moving a sleep into an HA script avoids dependency on the laptop but does not
by itself survive HA restart. A restoring timer can also expire while HA is
down: its completion event is not guaranteed to fire on startup. See the
[HA timer documentation](https://www.home-assistant.io/integrations/timer/).
Do not advertise either approach as a durable lease.

## Proposed narrow HA-side owner

Use an independently reviewed HA-side implementation for one configured light,
with an exclusive acquisition path and a persistent record containing:

- Exact entity, previous supported static RGB/off state and a random lease ID.
- Absolute UTC expiry, expected displayed state and ownership/context evidence.
- A pending-write marker set before changing the light; never guess ownership
  after a crash between the write and recording its resulting HA context.

Persist the record before changing the light. On normal expiry, explicit restore
or HA startup, reconcile that same record against the current light. Restore
only when ownership is still verifiable; preserve a detected manual override.
Retain and report ambiguous records instead of discarding them. Reject overlapping
leases, effects and unsupported snapshots. Do not run foreground and HA-side
restoration independently against the same light.

Startup must reconcile persisted absolute deadlines, not rely solely on timer
events. If HA or the light is unavailable, retain recovery information and
reconcile on recovery under an explicitly bounded retry policy. Restoration
cannot happen while the controller or HA is down; even a durable record does
not guarantee timely restoration during an outage.

This needs a real transaction/ownership design. HA state/context checks are not
atomic compare-and-set, and same-value manual actions may be indistinguishable.
Do not silently claim those existing limitations are solved. Security review
must also cover persistent storage, narrow callable services, supplied durations,
credential scope, startup reconciliation and event-trigger authority.

## Acceptance before offering durable mode

First commission the existing helper separately using a private configuration
and trusted credential injection. Preserve the snapshot and exact candidate
identity. Collect both API state and the operator's visual observations:

1. Display a short steady colour at the configured ceiling and verify restoration
   to the original supported state. Repeat from off, checking actual output.
2. Use a separate test configuration whose quiet-hours interval includes the
   current time. Verify suppression and no light service call; do not disable
   the operator's ordinary quiet-hours policy to make the test pass.
3. During a timed signal, change the light manually through HA. Verify that
   expiry preserves the override. Restore the original state only under explicit
   operator direction, not by overriding the helper's ownership decision.
4. Test interruption and retained-record recovery without deleting uncertainty.
   Existing offline tests cover failure paths; live fault injection needs its
   own approval and must not disrupt unrelated household devices.

For any later durable implementation, additionally test laptop death, HA restart
before and after expiry, light/proxy outages, lost write acknowledgements,
manual overrides and duplicate requests. Verify recovery from the exact
persistent record, not merely a green API response. Do not deliberately crash
or restart HA without separate authority. Provisioning or installing an HA-side
implementation requires separate scoped approval and independent review.

Rollback must stop only the new owner and remove only task-created entities
after resolving its active lease; preserve unrelated HA configuration. Existing
manual light controls must remain usable. No unattended mode is accepted until
these checks pass on the actual deployment.
