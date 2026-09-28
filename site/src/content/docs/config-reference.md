---
title: Config Reference
description: Klipper configuration reference for FOCI.
---

## `[foci <stepper>]`

Turns on the TMC4671 driver for one stepper channel. The section name
must match an existing Klipper stepper section, for example
`[foci stepper_x]` pairs with `[stepper_x]`. See
[Configuration](/getting-started/configuration/).

```
[foci stepper_x]
run_current:
#   Run current in amps. Must be provided.
encoder_ppr:
#   Encoder pulses per revolution. Must be provided.
#voltage_limit: 16000
#   Raw TMC4671 voltage-limit register value, 0 to 32767.
#encoder_direction: default
#   Set to `reversed` if FOCI_SELFTEST reports "encoder_direction
#   looks inverted".
#homing_current: 0
#   Current in amps used while homing against a sensorless virtual
#   endstop. 0 disables the homing-current clamp. Must stay below
#   run_current if set.
#stall_ceiling_mm: 1.0
#   Sensorless-homing stall detection. A fixed following-error limit
#   in mm. Crossing it always counts as a stall, from the first moment
#   of the move.
#stall_margin_mm: 0.15
#   How far above the axis's own normal following error, in mm, counts
#   as a stall once the move is underway. Must be less than
#   stall_ceiling_mm.
#stall_persistence: 3
#   How many times in a row the error has to stay past either
#   threshold before it's called a stall and motion stops.
#pid_torque_p:
#pid_torque_i:
#pid_flux_p:
#pid_flux_i:
#   Inner current-loop gains, 0 to 32767 each. Written automatically
#   by FOCI_SETUP. Set all four together if overriding manually.
#pid_position_p:
#pid_position_i:
#pid_velocity_p:
#pid_velocity_i:
#pid_velocity_limit:
#   Outer position/velocity loop gains, 0 to 32767 each
#   (pid_velocity_limit up to 65535). Written automatically by
#   FOCI_AUTOTUNE. Set all four PID fields together if overriding
#   manually.
#torque_filter_hz:
#flux_filter_hz:
#velocity_filter_hz:
#position_filter_hz:
#   Current-loop input filter cutoffs, in Hz. Omitted or 0 disables
#   each filter. torque_filter_hz/flux_filter_hz accept 10-10000,
#   velocity_filter_hz/position_filter_hz accept 10-1000.
#velocity_feedforward: False
#velocity_feedforward_gain: 1.0
#   Feed-forward correction for position-loop cruise lag, gain 0.0 to
#   8.0.
```

## `[foci]`

Optional, workspace-wide settings shared by every `[foci <stepper>]`
section. Omit this section entirely if you don't need it.

```
[foci]
#debug: False
#   Enables verbose debug logging.
```
