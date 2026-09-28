---
title: Sensorless Homing
description: Home an axis against its hard stop without an endstop switch.
---

FOCI can home an axis by detecting the motion stall from the encoder,
so that axis needs no endstop switch. Sensorless homing is optional.
Physical endstops keep working, so skip this page if you use them.

Do this after [Tuning](/getting-started/tuning/). The stall detector
measures how far the axis lags behind its commanded position, and that
lag depends on the tuned gains.

## Configure

Two changes per axis. In `[foci <stepper>]`, set `homing_current`, the
reduced current used while homing:

```ini
[foci <stepper>]
run_current: 1.0
encoder_ppr: 1000
homing_current: 0.4
```

In `[<stepper>]`, point the endstop at FOCI's virtual endstop:

```ini
[<stepper>]
endstop_pin: foci_<stepper>:virtual_endstop
```

- `homing_current` is required on each axis that uses the virtual
  endstop. Klipper reports a config error if it's missing. It must be
  above 0 and at least 0.05 A below `run_current`.
- Start at 30 to 50% of `run_current`.
- On CoreXY, both motors move for every X or Y home. On the motor whose
  axis doesn't use the virtual endstop, `homing_current` is optional.
  Without it, that motor homes at full `run_current`. Set it there too
  to reduce the current on both motors.

## Home

Set `homing_speed` in `[<stepper>]` to at least
`1.25 × 1000 × rotation_distance ÷ encoder_ppr` mm/s, which is 50 mm/s
for a `rotation_distance` of 40 and an `encoder_ppr` of 1000. Slower
than that, FOCI detects the stop later, so the axis presses harder
against it before homing completes. Common homing speeds are 80 to 120
mm/s.

Then home:

```gcode
G28 <axis>
```

## Verify

Home the axis 10 times. Every home should complete without an error.

## Troubleshooting

- **Triggers early, mid-travel.** Klipper retries once at the second
  homing speed, then reports an error. Raise `homing_current` by 0.1 A,
  raise `stall_margin_mm` by 0.05, or lower `homing_speed`, staying above
  the minimum. `stall_margin_mm` is how far the axis can lag behind its
  commanded position, above its normal lag, before it counts as a stall.
  Keep it below `stall_ceiling_mm`, the fixed lag limit that always
  counts as a stall.
- **"No trigger on <stepper> after full movement".** The toolhead never
  registered a stall. If it reached the hard stop, lower `stall_margin_mm`
  by 0.05. If it stopped short of the hard stop, lower `homing_speed`.

Change one value at a time, `RESTART`, and re-run the 10-home check.
