---
title: Bring-up
description: Bring up and commission a freshly flashed Ouroboros board.
---

Requires the `printer.cfg` from [Configuration](/getting-started/configuration/)
and a running Klipper. Run each command below once per axis (`stepper_x`,
then `stepper_y`).

## Self-test

```gcode
FOCI_SELFTEST STEPPER=stepper_x
```

Checks board and wiring health, independent of motor tuning. A passing run:

```text
  ADC calibration .................... PASS (offset_i0=..., offset_i1=...)
  Motor coil A ....................... PASS (current=...)
  Motor coil B ....................... PASS (current=...)
  Phase wiring ....................... PASS
  Encoder ............................ PASS
  Encoder direction .................. PASS
  R-model evidence ................... PASS
  L control-model evidence ........... PASS
FOCI_SELFTEST stepper_x: SUCCEEDED, all 8 stages passed.
```

Stage reference:

| Stage | Checks | On failure |
|---|---|---|
| ADC calibration | TMC4671 current-sense offsets | Board or chip fault, not wiring |
| Motor coil A / B | Each coil draws current when driven | Open or shorted phase. Check the motor connector |
| Phase wiring | Coils aren't cross-wired to the wrong driver channel | Swap the two motor phase pairs at the connector |
| Encoder | Encoder signal present and readable | Encoder cable disconnected or miswired |
| Encoder direction | Encoder counts the expected direction for commanded current | Not a wiring fault. Console reports `encoder_direction looks inverted`. Set `encoder_direction: reversed` in `[foci stepper_x]` and re-run |
| R-model / L control-model evidence | Resistance/inductance measurement quality | Motor moved during the test. Ensure it's unloaded and free to turn, then re-run |

## Setup

```gcode
FOCI_SETUP STEPPER=stepper_x
```

Identifies motor resistance and inductance and applies current gains.
Defaults to the `balanced` profile. Pass `PROFILE=conservative` or
`PROFILE=stiff` to change it.

```text
FOCI_SETUP stepper_x: SUCCEEDED, resistance/inductance identified, current gains applied.
```

### Warnings

If the measurement wasn't fully clean, the console also prints a warning
line, for example:

```text
FOCI stepper_x inner confidence: coil R mismatch, theta/tau ratio
```

| Warning | Cause | Action |
|---|---|---|
| coil R mismatch, coil control-model tau mismatch, theta/tau ratio | Electrical asymmetry between the two coils | Check the connector, re-run |
| current gains fell back to defaults, host-default confidence (no fresh measurement) | Identification run didn't get a clean measurement | Ensure the motor is unloaded and free to move, re-run |

A warning doesn't block the axis from working. Firmware tunes it more
conservatively than a clean measurement would allow, so you can proceed
to bring-up the next axis or start homing. To clear a warning instead,
apply the fix from the table above and re-run `FOCI_SETUP` before
`SAVE_CONFIG`.

## Save

```gcode
SAVE_CONFIG
```

Persists the identified resistance, inductance, and current gains to
`printer.cfg`, and restarts Klipper. Run self-test and setup for both
axes first, so one `SAVE_CONFIG` covers both.

## First home

Keep a hand on emergency stop (`M112`, or your printer's physical
switch) in case an axis moves the wrong way or doesn't stop at the
endstop.

```gcode
G28 X
```

```gcode
G28 Y
```

Each axis moves and homes correctly, but isn't tuned for production
motion yet. Continue with [Tuning](/getting-started/tuning/) before
printing.
